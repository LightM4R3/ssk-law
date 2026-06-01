"""Bills API views – matches API_SPEC.md endpoints."""

import math
import json

from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Bill, BillSummary, Category
from .serializers import BillDetailSerializer, BillListSerializer, CategorySerializer
from services.ollama import search_bills, analyze_user_query, chat_reply
from chat.masking import mask_personal_info
from chat.models import ChatSession, ChatMessage
from django.db.models import Q


# ---------------------------------------------------------------------------
# GET /api/categories
# ---------------------------------------------------------------------------
@api_view(["GET"])
def categories_view(request):
    """분야 목록 + 법안 개수."""
    cats = (
        Category.objects
        .annotate(count=Count("bills"))
        .order_by("sort_order")
    )
    total = Bill.objects.count()

    data = [{"slug": "all", "label": "전체", "count": total}]
    data += list(cats.values("slug", "label", "count"))

    serializer = CategorySerializer(data, many=True)
    return Response({"categories": serializer.data})


# ---------------------------------------------------------------------------
# GET /api/home/picks
# ---------------------------------------------------------------------------
@api_view(["GET"])
def picks_view(request):
    """홈 추천 법안 5건 (조회수 상위 + 요약 있는 법안)."""
    bills = (
        Bill.objects
        .filter(summary__isnull=False)
        .select_related("summary")
        .prefetch_related("bill_categories__category", "similar_bills")
        .order_by("-view_count")[:5]
    )
    if not bills:
        # fallback: just return latest 5
        bills = (
            Bill.objects
            .select_related("summary")
            .prefetch_related("bill_categories__category", "similar_bills")
            .order_by("-proposed_at")[:5]
        )
    serializer = BillListSerializer(bills, many=True)
    return Response({"picks": serializer.data})


# ---------------------------------------------------------------------------
# GET /api/bills
# ---------------------------------------------------------------------------
SORT_FIELDS = {
    "-proposed_at": "-proposed_at",
    "proposed_at": "proposed_at",
    "-view_count": "-view_count",
    "view_count": "view_count",
}


@api_view(["GET"])
def bills_list_view(request):
    """최신 법안 목록 (분야 필터 + 정렬 + 페이지네이션)."""
    category = request.query_params.get("category", "all")
    sort = request.query_params.get("sort", "-proposed_at")
    page = int(request.query_params.get("page", 1))
    page_size = min(int(request.query_params.get("page_size", 20)), 100)

    qs = Bill.objects.select_related("summary").prefetch_related(
        "bill_categories__category", "similar_bills"
    )

    if category != "all":
        qs = qs.filter(bill_categories__category__slug=category)

    order = SORT_FIELDS.get(sort, "-proposed_at")
    qs = qs.order_by(order)

    total_count = qs.count()
    total_pages = max(1, math.ceil(total_count / page_size))
    offset = (page - 1) * page_size
    bills = qs[offset : offset + page_size]

    serializer = BillListSerializer(bills, many=True)
    return Response(
        {
            "bills": serializer.data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
            },
        }
    )


# ---------------------------------------------------------------------------
# GET /api/bills/<bill_id>
# ---------------------------------------------------------------------------
@api_view(["GET"])
def bill_detail_view(request, bill_id):
    """법안 상세."""
    try:
        bill = (
            Bill.objects
            .select_related("summary")
            .prefetch_related("bill_categories__category", "similar_bills")
            .get(bill_id=bill_id)
        )
    except Bill.DoesNotExist:
        # Also try by numeric pk
        try:
            bill = (
                Bill.objects
                .select_related("summary")
                .prefetch_related("bill_categories__category", "similar_bills")
                .get(pk=bill_id)
            )
        except (Bill.DoesNotExist, ValueError):
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "해당 법안을 찾을 수 없습니다."}},
                status=status.HTTP_404_NOT_FOUND,
            )

    # Increment view count
    Bill.objects.filter(pk=bill.pk).update(view_count=bill.view_count + 1)

    serializer = BillDetailSerializer(bill)
    return Response(serializer.data)


# ---------------------------------------------------------------------------
# POST /api/search
# ---------------------------------------------------------------------------
@api_view(["POST"])
def search_view(request):
    """자연어 검색 (AI)."""
    query = request.data.get("query", "").strip()
    if not query:
        return Response(
            {"error": {"code": "INVALID_QUERY", "message": "검색어를 입력해 주세요."}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 1. 개인정보 마스킹 처리
    masked_query = mask_personal_info(query)

    # 2. Zero-shot 구조화 분석
    analysis = analyze_user_query(masked_query)
    if not analysis:
        analysis = {
            "summary": "구조화 분석 실패",
            "issue": "구조화 분석 실패",
            "keywords": [],
            "risk_level": "Low"
        }

    # 3. 위험 질문 차단 검사 (법 회피·범죄·증거 인멸)
    dangerous_keywords = [
        '마약', '탈세', '증거인멸', '증거 인멸', '블랙박스 삭제', '블랙박스 영상 삭제', 
        '필로폰', '대마', '안 걸리는', '피하는 팁', '세무조사 피', '영구 삭제', 
        '카카오톡 삭제', '대화 삭제', '대화 내역 삭제', '카카오톡 대화 내역', '거래 시 안',
        '처벌 수위를 낮추기 위해 블랙박스'
    ]

    is_dangerous = False
    risk_level = str(analysis.get("risk_level", "Low")).strip().upper()
    if risk_level == "HIGH":
        is_dangerous = True

    text_to_check = (masked_query + " " + str(analysis.get("summary", "")) + " " + str(analysis.get("issue", ""))).lower()
    for dk in dangerous_keywords:
        if dk.lower() in text_to_check:
            is_dangerous = True
            analysis["risk_level"] = "High"
            break

    # 검색 세션 생성 및 메시지 저장용
    session_key = request.data.get("session_key") or "search_session"
    session, _ = ChatSession.objects.get_or_create(session_key=session_key)

    if is_dangerous:
        intro = "범죄 모의, 증거 인멸, 법망 회피 등 위법 행위와 관련된 질문에는 답변을 제공할 수 없습니다."
        
        # DB 저장 (스냅샷 저장)
        ChatMessage.objects.create(session=session, role="user", content=masked_query)
        ChatMessage.objects.create(
            session=session,
            role="assistant",
            content=intro,
            related_bill_ids=json.dumps([]),
            snapshot=analysis
        )

        return Response(
            {
                "intro": intro,
                "ids": [],
                "bills": [],
                "snapshot": analysis
            }
        )

    # 4. 관련 법안/법령 검색
    keywords = analysis.get("keywords", [])
    matched = _search_bills_by_keywords_for_search(keywords)

    # 5. context 구축
    if matched:
        context_lines = []
        for b in matched:
            cats = ", ".join(bc.category.label for bc in b.bill_categories.all())
            s1 = ""
            try:
                s1 = b.summary.summary_1
            except BillSummary.DoesNotExist:
                pass
            context_lines.append(f"- [{b.bill_id}] {b.title} ({cats}) - {s1[:80]}")
        context = "\n".join(context_lines)
    else:
        # fallback context
        bills = Bill.objects.select_related("summary").prefetch_related("bill_categories__category")
        context_lines = []
        for b in bills[:30]:
            cats = ", ".join(bc.category.label for bc in b.bill_categories.all())
            s1 = ""
            try:
                s1 = b.summary.summary_1
            except BillSummary.DoesNotExist:
                pass
            context_lines.append(f"- [{b.bill_id}] {b.title} ({cats}) - {s1[:80]}")
        context = "\n".join(context_lines)

    # 6. 답변 생성 (단정 표현 방지 지침 및 Disclaimer 자동 삽입)
    intro = chat_reply(masked_query, context)
    if not intro:
        intro = (
            "지금은 AI 서비스에 연결할 수 없어요. 😅\n"
            "잠시 뒤에 다시 시도해 주세요!\n\n"
            "그 사이에 최신 법안을 한번 둘러보는 건 어때요?"
        )
    
    DISCLAIMER = "\n\n---\n*면책조항: 본 답변은 참고용 법률 정보 및 국회 발의안 데이터에 기반하여 제공되는 것이며, 어떠한 법적 효력이나 공식적인 법률 자문을 대신할 수 없습니다. 구체적인 사안에 대해서는 반드시 법률 전문가와 상담하시기 바랍니다.*"
    intro = intro + DISCLAIMER

    # 7. 스냅샷 저장
    ChatMessage.objects.create(session=session, role="user", content=masked_query)
    
    related_ids_json = json.dumps([b.bill_id for b in matched]) if matched else json.dumps([])
    ChatMessage.objects.create(
        session=session,
        role="assistant",
        content=intro,
        related_bill_ids=related_ids_json,
        snapshot=analysis
    )

    serializer = BillListSerializer(matched, many=True)
    return Response(
        {
            "intro": intro,
            "ids": [b.bill_id for b in matched],
            "bills": serializer.data,
            "snapshot": analysis
        }
    )


def _search_bills_by_keywords_for_search(keywords: list) -> list:
    """검색용 분석된 키워드를 활용해 법안 DB를 검색합니다."""
    if not keywords:
        return []
    
    query = Q()
    for kw in keywords:
        if kw:
            query |= Q(title__icontains=kw) | Q(summary__summary_1__icontains=kw)
            
    return list(Bill.objects.filter(query).prefetch_related("bill_categories__category", "similar_bills").distinct()[:5])


def _keyword_fallback(query, bills):
    """Simple keyword matching fallback when AI is unavailable."""
    q = query.lower()
    tokens = [t for t in q.replace("?", "").replace("!", "").split() if len(t) > 1]

    scored = []
    for b in bills:
        cats_text = " ".join(bc.category.label for bc in b.bill_categories.all())
        hay = f"{b.title} {cats_text}".lower()
        score = 0
        if q in hay:
            score += 5
        for t in tokens:
            if t in hay:
                score += 1
        if score > 0:
            scored.append((score, b))

    scored.sort(key=lambda x: -x[0])
    matched = [b for _, b in scored[:5]]

    if matched:
        intro = f'"{query}"와(과) 관련된 법안 {len(matched)}건을 슥 찾아봤어요.'
    else:
        # Return first 3 as fallback
        matched = list(bills[:3])
        intro = f'"{query}" 관련 법안을 정확히 찾기 어려워서, 최신 법안을 보여드릴게요.'

    return intro, matched
