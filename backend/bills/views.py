"""Bills API views – matches API_SPEC.md endpoints."""

import math

from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Bill, BillSummary, Category
from .serializers import BillDetailSerializer, BillListSerializer, CategorySerializer
from services.ollama import search_bills


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

    # Build compact bill list for AI context
    bills = Bill.objects.select_related("summary").prefetch_related(
        "bill_categories__category"
    )
    lines = []
    for b in bills:
        cats = ", ".join(
            bc.category.label for bc in b.bill_categories.all()
        )
        s1 = ""
        try:
            s1 = b.summary.summary_1[:60]
        except BillSummary.DoesNotExist:
            s1 = b.title[:60]
        lines.append(f"- {b.bill_id} | {b.title} | {cats} | {s1}")

    compact = "\n".join(lines)

    # Try AI search
    ai_result = search_bills(query, compact)

    if ai_result and ai_result.get("ids"):
        ids = ai_result["ids"]
        intro = ai_result.get("intro", f'"{query}" 관련 법안을 찾았어요.')
        matched = Bill.objects.filter(bill_id__in=ids).select_related("summary").prefetch_related(
            "bill_categories__category", "similar_bills"
        )
    else:
        # Keyword fallback
        intro, matched = _keyword_fallback(query, bills)

    serializer = BillListSerializer(matched, many=True)
    return Response(
        {
            "intro": intro,
            "ids": [b.bill_id for b in matched],
            "bills": serializer.data,
        }
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
