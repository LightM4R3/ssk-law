"""Chat API views – matches API_SPEC.md."""

import json
import uuid

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from bills.models import Bill, BillSummary
from .models import ChatMessage, ChatSession
from .serializers import ChatMessageSerializer, ChatRequestSerializer
from services.ollama import chat_reply


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

    # Get or create session
    session, _ = ChatSession.objects.get_or_create(session_key=session_key)

    # Save user message
    ChatMessage.objects.create(session=session, role="user", content=message)

    # Build context from bills DB
    context = _build_bill_context()

    # Build history from recent messages
    recent = session.messages.order_by("-created_at")[:10]
    history_lines = []
    for msg in reversed(list(recent)):
        prefix = "사용자" if msg.role == "user" else "어시스턴트"
        history_lines.append(f"{prefix}: {msg.content}")
    history = "\n".join(history_lines)

    # Call AI
    reply_text = chat_reply(message, context, history)

    if not reply_text:
        reply_text = (
            "지금은 AI 서비스에 연결할 수 없어요. 😅\n"
            "잠시 뒤에 다시 시도해 주세요!\n\n"
            "그 사이에 최신 법안을 한번 둘러보는 건 어때요?"
        )

    # Find related bills mentioned in the response
    related = _extract_related_bills(reply_text)

    # Save assistant message
    related_ids_json = json.dumps([b.bill_id for b in related]) if related else ""
    ChatMessage.objects.create(
        session=session,
        role="assistant",
        content=reply_text,
        related_bill_ids=related_ids_json,
    )

    return Response(
        {
            "session_key": session_key,
            "reply": reply_text,
            "related_bills": [
                {"id": b.bill_id, "title": b.title} for b in related
            ],
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


def _extract_related_bills(reply_text: str) -> list:
    """Try to find bill titles mentioned in the AI reply."""
    bills = Bill.objects.all()[:50]
    found = []
    for b in bills:
        # Check if any significant part of the title appears in the reply
        short_title = b.title[:15]
        if short_title and short_title in reply_text:
            found.append(b)
    return found[:5]
