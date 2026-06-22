"""Bills API views – matches API_SPEC.md endpoints."""

import math
import json
import re

from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Bill, BillSummary, Category, SyncRun
from .serializers import BillDetailSerializer, BillListSerializer, CategorySerializer
from services.ollama import PLAIN_DISCLAIMER, explain_search
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
        .prefetch_related("bill_categories__category", "similar_bills", "processing_tasks")
        .order_by("-view_count")[:5]
    )
    if not bills:
        # fallback: just return latest 5
        bills = (
            Bill.objects
            .select_related("summary")
            .prefetch_related("bill_categories__category", "similar_bills", "processing_tasks")
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
        "bill_categories__category", "similar_bills", "processing_tasks"
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
            .prefetch_related("bill_categories__category", "similar_bills", "processing_tasks")
            .get(bill_id=bill_id)
        )
    except Bill.DoesNotExist:
        # Also try by numeric pk
        try:
            bill = (
                Bill.objects
                .select_related("summary")
                .prefetch_related("bill_categories__category", "similar_bills", "processing_tasks")
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
# GET /api/sync/status
# ---------------------------------------------------------------------------
@api_view(["GET"])
def sync_status_view(request):
    """최근 OpenAPI 동기화 상태. 외부 서비스를 호출하지 않습니다."""
    last_attempt = SyncRun.objects.exclude(status="skipped").first()
    last_success = SyncRun.objects.filter(status__in=["success", "no_changes"]).first()
    last_new_bill = SyncRun.objects.filter(created_count__gt=0).exclude(status="failed").first()

    return Response(
        {
            "lastAttemptAt": last_attempt.started_at if last_attempt else None,
            "lastSuccessAt": last_success.finished_at if last_success else None,
            "lastNewBillAt": last_new_bill.finished_at if last_new_bill else None,
            "status": last_attempt.status if last_attempt else "never",
            "createdCount": last_attempt.created_count if last_attempt else 0,
            "error": last_attempt.error_message if last_attempt else "",
        }
    )


# ---------------------------------------------------------------------------
# POST /api/search
# ---------------------------------------------------------------------------
@api_view(["POST"])
def search_view(request):
    """Return DB search results immediately without waiting for the LLM."""
    query = request.data.get("query", "").strip()
    if not query:
        return Response(
            {"error": {"code": "INVALID_QUERY", "message": "검색어를 입력해 주세요."}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    masked_query = mask_personal_info(query)
    analysis = _analyze_search_query(masked_query)
    is_dangerous = analysis["risk_level"] == "High"
    session_key = request.data.get("session_key") or "search_session"
    session, _ = ChatSession.objects.get_or_create(session_key=session_key)
    ChatMessage.objects.create(session=session, role="user", content=masked_query)

    if is_dangerous:
        intro = "범죄 모의, 증거 인멸, 법망 회피 등 위법 행위와 관련된 질문에는 답변을 제공할 수 없습니다."
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
                "snapshot": analysis,
                "aiPending": False,
            }
        )

    keywords = analysis.get("keywords", [])
    matched = _search_bills_by_keywords_for_search(keywords)
    if not matched:
        matched = list(
            Bill.objects.select_related("summary")
            .prefetch_related("bill_categories__category", "similar_bills", "processing_tasks")
            .order_by("-proposed_at")[:3]
        )

    serializer = BillListSerializer(matched, many=True)
    return Response(
        {
            "intro": f"관련 법안 {len(matched)}건을 먼저 찾았습니다.",
            "ids": [b.bill_id for b in matched],
            "bills": serializer.data,
            "snapshot": analysis,
            "aiPending": True,
        }
    )


# ---------------------------------------------------------------------------
# POST /api/search/explain
# ---------------------------------------------------------------------------
@api_view(["POST"])
def search_explain_view(request):
    """Generate the optional AI explanation after DB results are rendered."""
    query = request.data.get("query", "").strip()
    if not query:
        return Response(
            {"error": {"code": "INVALID_QUERY", "message": "검색어를 입력해 주세요."}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    masked_query = mask_personal_info(query)
    analysis = _analyze_search_query(masked_query)
    if analysis["risk_level"] == "High":
        return Response(
            {
                "intro": "범죄 모의, 증거 인멸, 법망 회피 등 위법 행위와 관련된 질문에는 답변을 제공할 수 없습니다.",
                "snapshot": analysis,
                "aiStatus": "blocked",
            }
        )

    matched = _search_bills_by_keywords_for_search(analysis["keywords"])
    if not matched:
        matched = list(
            Bill.objects.select_related("summary")
            .prefetch_related("bill_categories__category")
            .order_by("-proposed_at")[:3]
        )
    context = _build_search_context(matched)
    intro = explain_search(masked_query, context)
    ai_status = "ready" if intro else "unavailable"
    if not intro:
        intro = f"관련 법안 {len(matched)}건을 찾았습니다. AI 설명은 잠시 후 다시 시도해 주세요."
    intro = f"{intro}\n{PLAIN_DISCLAIMER}"

    session_key = request.data.get("session_key") or "search_session"
    session, _ = ChatSession.objects.get_or_create(session_key=session_key)
    ChatMessage.objects.create(
        session=session,
        role="assistant",
        content=intro,
        related_bill_ids=json.dumps([bill.bill_id for bill in matched]),
        snapshot=analysis,
    )
    return Response({"intro": intro, "snapshot": analysis, "aiStatus": ai_status})


DANGEROUS_SEARCH_TERMS = (
    "마약",
    "탈세",
    "증거인멸",
    "증거 인멸",
    "블랙박스 삭제",
    "블랙박스 영상 삭제",
    "필로폰",
    "대마",
    "안 걸리는",
    "피하는 팁",
    "세무조사 피",
    "영구 삭제",
    "카카오톡 삭제",
    "대화 내역 삭제",
    "거래 시 안",
)

SEARCH_STOPWORDS = {
    "관련",
    "법안",
    "법률",
    "알려줘",
    "알려주세요",
    "궁금해",
    "궁금한데",
    "대한",
    "대해",
    "어떤",
}


def _analyze_search_query(query):
    tokens = re.findall(r"[가-힣A-Za-z0-9]+", query)
    keywords = []
    for token in tokens:
        normalized = token.strip().lower()
        if len(normalized) < 2 or normalized in SEARCH_STOPWORDS or normalized in keywords:
            continue
        keywords.append(normalized)
        if len(keywords) == 5:
            break
    dangerous = any(term in query.lower() for term in DANGEROUS_SEARCH_TERMS)
    return {
        "summary": f"'{query}' 관련 법안 검색",
        "issue": "검색어와 관련된 국회 발의안 확인",
        "keywords": keywords,
        "risk_level": "High" if dangerous else "Low",
    }


def _build_search_context(bills):
    lines = []
    for bill in bills[:5]:
        categories = ", ".join(
            mapping.category.label for mapping in bill.bill_categories.all()
        )
        try:
            summary = " ".join(
                part
                for part in (
                    bill.summary.summary_1,
                    bill.summary.summary_2,
                    bill.summary.summary_3,
                )
                if part
            )
        except BillSummary.DoesNotExist:
            summary = "요약 준비 중"
        lines.append(f"[{bill.bill_id}] {bill.title} | {categories} | {summary[:240]}")
    return "\n".join(lines)


def _search_bills_by_keywords_for_search(keywords: list) -> list:
    """검색용 분석된 키워드를 활용해 법안 DB를 검색합니다."""
    if not keywords:
        return []
    
    query = Q()
    for kw in keywords:
        if kw:
            query |= (
                Q(title__icontains=kw)
                | Q(committee__icontains=kw)
                | Q(summary__summary_1__icontains=kw)
                | Q(summary__summary_2__icontains=kw)
                | Q(summary__summary_3__icontains=kw)
                | Q(bill_categories__category__label__icontains=kw)
            )
            
    return list(
        Bill.objects.filter(query)
        .select_related("summary")
        .prefetch_related("bill_categories__category", "similar_bills", "processing_tasks")
        .distinct()[:5]
    )


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
