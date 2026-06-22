"""Chat API views – matches API_SPEC.md."""

import json
import uuid

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q

from bills.models import Bill, BillSummary
from .models import ChatMessage, ChatSession
from .serializers import ChatMessageSerializer, ChatRequestSerializer
from .masking import mask_personal_info
from services.ollama import PLAIN_DISCLAIMER, analyze_user_query, chat_reply


# ---------------------------------------------------------------------------
# POST /api/chat
# ---------------------------------------------------------------------------
@api_view(["POST"])
def chat_view(request):
    """챗봇 메시지 전송."""
    ser = ChatRequestSerializer(data=request.data)
    if not ser.is_valid():
        return Response(
            {"error": {"code": "INVALID_MESSAGE", "message": "질문을 입력해 주세요."}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    session_key = ser.validated_data.get("session_key") or str(uuid.uuid4())
    message = ser.validated_data["message"]

    # 1. 개인정보 마스킹 처리
    masked_message = mask_personal_info(message)

    # 2. Get or create session
    session, _ = ChatSession.objects.get_or_create(session_key=session_key)

    # 3. Zero-shot 구조화 분석
    analysis = analyze_user_query(masked_message)
    if not analysis:
        # LLM 분석 실패 시 기본 구조화 정보 생성
        analysis = {
            "summary": "구조화 분석 실패",
            "issue": "구조화 분석 실패",
            "keywords": [],
            "risk_level": "Low"
        }

    # 4. 위험 질문 차단 검사 (법 회피·범죄·증거 인멸)
    dangerous_keywords = [
        '마약', '탈세', '증거인멸', '증거 인멸', '블랙박스 삭제', '블랙박스 영상 삭제', 
        '필로폰', '대마', '안 걸리는', '피하는 팁', '세무조사 피', '영구 삭제', 
        '카카오톡 삭제', '대화 삭제', '대화 내역 삭제', '카카오톡 대화 내역', '거래 시 안',
        '처벌 수위를 낮추기 위해 블랙박스'
    ]

    is_dangerous = False
    
    # 위험도 레벨이 HIGH인 경우
    risk_level = str(analysis.get("risk_level", "Low")).strip().upper()
    if risk_level == "HIGH":
        is_dangerous = True

    # 질문 원본 또는 요약/쟁점에 위험 키워드가 포함된 경우
    text_to_check = (masked_message + " " + str(analysis.get("summary", "")) + " " + str(analysis.get("issue", ""))).lower()
    for dk in dangerous_keywords:
        if dk.lower() in text_to_check:
            is_dangerous = True
            analysis["risk_level"] = "High"  # 강제 위험도 업그레이드
            break

    if is_dangerous:
        # 차단 답변 구성
        reply_text = "범죄 모의, 증거 인멸, 법망 회피 등 위법 행위와 관련된 질문에는 답변을 제공할 수 없습니다."
        
        # DB 저장 (마스킹된 질문 및 차단 답변)
        ChatMessage.objects.create(session=session, role="user", content=masked_message)
        ChatMessage.objects.create(
            session=session,
            role="assistant",
            content=reply_text,
            related_bill_ids=json.dumps([]),
            snapshot=analysis
        )

        return Response(
            {
                "session_key": session_key,
                "reply": reply_text,
                "related_bills": [],
                "snapshot": analysis
            }
        )

    # 5. 관련 법안/법령 검색
    keywords = analysis.get("keywords", [])
    related_bills = _search_bills_by_keywords(keywords)

    # 6. context 구축 (검색 결과가 있으면 이를 바탕으로, 없으면 전체 법안 중 일부로 폴백)
    if related_bills:
        context_lines = []
        for b in related_bills:
            cats = ", ".join(bc.category.label for bc in b.bill_categories.all())
            summary = ""
            try:
                summary = b.summary.summary_1
            except BillSummary.DoesNotExist:
                pass
            context_lines.append(f"- [{b.bill_id}] {b.title} ({cats}) - {summary[:80]}")
        context = "\n".join(context_lines)
    else:
        context = _build_bill_context()

    # 7. Build history
    recent = session.messages.order_by("-created_at")[:10]
    history_lines = []
    for msg in reversed(list(recent)):
        prefix = "사용자" if msg.role == "user" else "어시스턴트"
        history_lines.append(f"{prefix}: {msg.content}")
    history = "\n".join(history_lines)

    # 8. AI 답변 생성 (단정 표현 방지 지침 적용된 프롬프트 사용)
    reply_text = chat_reply(masked_message, context, history)

    if not reply_text:
        reply_text = (
            "지금은 AI 서비스에 연결할 수 없어요. 😅\n"
            "잠시 뒤에 다시 시도해 주세요!\n\n"
            "그 사이에 최신 법안을 한번 둘러보는 건 어때요?"
        )
    
    # Disclaimer 자동 삽입
    reply_text = f"{reply_text}\n{PLAIN_DISCLAIMER}"

    # 9. DB 저장 전 마스킹 확인 및 최종 저장
    ChatMessage.objects.create(session=session, role="user", content=masked_message)
    
    related_ids_json = json.dumps([b.bill_id for b in related_bills]) if related_bills else json.dumps([])
    ChatMessage.objects.create(
        session=session,
        role="assistant",
        content=reply_text,
        related_bill_ids=related_ids_json,
        snapshot=analysis
    )

    return Response(
        {
            "session_key": session_key,
            "reply": reply_text,
            "related_bills": [
                {"id": b.bill_id, "title": b.title} for b in related_bills
            ],
            "snapshot": analysis
        }
    )


# ---------------------------------------------------------------------------
# GET /api/chat/history
# ---------------------------------------------------------------------------
@api_view(["GET"])
def chat_history_view(request):
    """대화 내역 조회."""
    session_key = request.query_params.get("session_key", "")
    if not session_key:
        return Response(
            {"error": {"code": "INVALID_PARAM", "message": "session_key를 입력해 주세요."}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        session = ChatSession.objects.get(session_key=session_key)
    except ChatSession.DoesNotExist:
        return Response(
            {"error": {"code": "NOT_FOUND", "message": "해당 세션을 찾을 수 없습니다."}},
            status=status.HTTP_404_NOT_FOUND,
        )

    messages = session.messages.order_by("created_at")
    serializer = ChatMessageSerializer(messages, many=True)
    return Response(
        {
            "session_key": session_key,
            "messages": serializer.data,
        }
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_bill_context() -> str:
    """Build a compact text representation of bills for AI context."""
    bills = Bill.objects.select_related("summary").prefetch_related(
        "bill_categories__category"
    )[:30]  # limit for prompt size
    lines = []
    for b in bills:
        cats = ", ".join(bc.category.label for bc in b.bill_categories.all())
        summary = ""
        try:
            summary = b.summary.summary_1
        except BillSummary.DoesNotExist:
            pass
        lines.append(f"- [{b.bill_id}] {b.title} ({cats}) - {summary[:80]}")
    return "\n".join(lines)


def _search_bills_by_keywords(keywords: list) -> list:
    """분석된 키워드를 활용해 법안 DB를 검색합니다."""
    if not keywords:
        return []
    
    query = Q()
    for kw in keywords:
        if kw:
            query |= Q(title__icontains=kw) | Q(summary__summary_1__icontains=kw)
            
    # 관련 법안 최대 5개 매칭
    return list(Bill.objects.filter(query).prefetch_related("bill_categories__category").distinct()[:5])
