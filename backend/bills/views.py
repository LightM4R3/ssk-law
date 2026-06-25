"""Bills API views – matches API_SPEC.md endpoints."""

import math
import json
import re
from collections import Counter

from django.db.models import Case, Count, IntegerField, Q, When
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Bill, BillSummary, Category, SyncRun
from .serializers import (
    BillDetailSerializer,
    BillListSerializer,
    CategorySerializer,
    SimilarBillSerializer,
)
from .services.similarity import ensure_similar_bills
from services.ollama import analyze_user_query, explain_search
from chat.masking import mask_personal_info
from chat.models import ChatSession, ChatMessage


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
    bills = list(
        Bill.objects
        .filter(summary__isnull=False)
        .select_related("summary")
        .prefetch_related("bill_categories__category", "similar_bills", "processing_tasks")
        .order_by("-view_count")[:5]
    )
    if not bills:
        # fallback: just return latest 5
        bills = list(
            Bill.objects
            .select_related("summary")
            .prefetch_related("bill_categories__category", "similar_bills", "processing_tasks")
            .order_by("-proposed_at")[:5]
        )
    for bill in bills:
        ensure_similar_bills(bill, limit=5)
    serializer = BillListSerializer(bills, many=True, context={"include_similar": True})
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
    ).annotate(
        summary_sort=Case(
            When(summary__isnull=False, then=0),
            default=1,
            output_field=IntegerField(),
        )
    )

    if category != "all":
        qs = qs.filter(bill_categories__category__slug=category)

    order = SORT_FIELDS.get(sort, "-proposed_at")
    order_fields = ["summary_sort", order]
    if order not in ("-proposed_at", "proposed_at"):
        order_fields.append("-proposed_at")
    qs = qs.order_by(*order_fields)

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
# GET /api/bills/<bill_id>/similar
# ---------------------------------------------------------------------------
@api_view(["GET"])
def bill_similar_view(request, bill_id):
    """Lazy-load similar bills for one bill from the local DB/cache only."""
    limit = min(max(int(request.query_params.get("limit", 5)), 1), 10)
    refresh = request.query_params.get("refresh") == "1"
    try:
        bill = (
            Bill.objects
            .select_related("summary")
            .prefetch_related("bill_categories__category")
            .get(bill_id=bill_id)
        )
    except Bill.DoesNotExist:
        try:
            bill = (
                Bill.objects
                .select_related("summary")
                .prefetch_related("bill_categories__category")
                .get(pk=bill_id)
            )
        except (Bill.DoesNotExist, ValueError):
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "?대떦 踰뺤븞??李얠쓣 ???놁뒿?덈떎."}},
                status=status.HTTP_404_NOT_FOUND,
            )

    similar = ensure_similar_bills(bill, limit=limit, refresh=refresh)
    return Response(
        {
            "billId": bill.bill_id,
            "similar": SimilarBillSerializer(similar, many=True).data,
        }
    )


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
    analysis = _build_search_analysis(masked_query)
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

    if analysis.get("clarificationNeeded"):
        intro = _compose_clarification_answer(analysis)
        ChatMessage.objects.create(
            session=session,
            role="assistant",
            content=intro,
            related_bill_ids=json.dumps([]),
            snapshot=analysis,
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

    matched = _search_bills_by_analysis(analysis)
    analysis["displayTags"] = _build_search_display_tags(analysis, matched)
    intro = _compose_db_search_answer(masked_query, analysis, matched)

    serializer = BillListSerializer(matched, many=True)
    return Response(
        {
            "intro": intro,
            "ids": [b.bill_id for b in matched],
            "bills": serializer.data,
            "snapshot": analysis,
            "aiPending": bool(matched),
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
    analysis = _build_search_analysis(masked_query)
    if analysis["risk_level"] == "High":
        return Response(
            {
                "intro": "범죄 모의, 증거 인멸, 법망 회피 등 위법 행위와 관련된 질문에는 답변을 제공할 수 없습니다.",
                "snapshot": analysis,
                "aiStatus": "blocked",
            }
        )

    if analysis.get("clarificationNeeded"):
        return Response({
            "intro": _compose_clarification_answer(analysis),
            "snapshot": analysis,
            "aiStatus": "needs_clarification",
        })

    matched = _search_bills_by_analysis(analysis)
    analysis["displayTags"] = _build_search_display_tags(analysis, matched)
    if not matched:
        intro = _compose_db_search_answer(masked_query, analysis, matched)
        return Response({"intro": intro, "snapshot": analysis, "aiStatus": "ready"})

    context = _build_search_context(matched)
    intro = explain_search(masked_query, context)
    ai_status = "ready" if intro else "unavailable"
    if not intro:
        intro = _compose_db_search_answer(masked_query, analysis, matched)

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
    "관련된",
    "관련한",
    "법안",
    "법의안",
    "법률",
    "법률안",
    "발의안",
    "알려줘",
    "알려주세요",
    "궁금해",
    "궁금한데",
    "대한",
    "대해",
    "어떤",
    "뭐가",
    "뭔가",
    "있어",
    "있나요",
    "있냐",
    "된게",
    "단계",
    "이미",
}

SEARCH_TOPIC_SYNONYMS = {
    "조세": ["조세", "세금", "과세", "지방세", "국세", "소득세", "법인세", "부가가치세", "부가세", "종부세", "상속세", "증여세", "세제", "조세특례", "공제"],
    "교육": ["교육", "학교", "급식", "학생", "고등학생", "중학생", "청소년", "교원", "대학", "초등", "중등", "고등학교"],
    "교통사고": ["교통사고", "교통", "사고", "운전", "보행자", "도로", "차량", "자동차"],
    "주거": ["주거", "주택", "전세", "월세", "임대차", "임차", "보증금", "부동산"],
    "보건": ["보건", "건강", "의료", "병원", "환자", "질병", "감염병", "국민건강보험"],
    "복지": ["복지", "장애", "노인", "아동", "청년", "수급", "연금", "돌봄"],
    "노동": ["노동", "근로", "임금", "고용", "해고", "노조", "산재"],
    "안전": ["안전", "재난", "소방", "범죄", "보호구역", "생활안전"],
    "디지털": ["디지털", "AI", "ai", "인공지능", "개인정보", "정보통신", "플랫폼", "데이터"],
    "기후": ["기후", "기후위기", "기후변화", "탄소", "탄소중립", "온실가스", "환경", "에너지", "재생에너지", "녹색", "온난화", "배출권", "미세먼지"],
    "농수산업": ["농수산업", "농업", "농촌", "농어촌", "수산", "수산업", "어업", "식품산업", "스마트농업", "농산물"],
    "기업": ["기업", "중소기업", "벤처", "벤처기업", "창업", "스타트업", "소상공인", "사업자", "투자"],
    "청년": ["청년", "청년창업", "청년고용", "청년기업", "청년일자리"],
    "일자리": ["일자리", "고용", "취업", "채용", "근로", "노동시장"],
}

SEARCH_STAGE_TERMS = {
    "발의": "proposed",
    "제안": "proposed",
    "위원회": "committee",
    "심사": "committee",
    "소위": "committee",
    "본회의": "plenary",
    "상정": "plenary",
    "의결": "plenary",
    "통과": "passed",
    "공포": "passed",
}

SEARCH_RESULT_TERMS = {
    "통과": ["original_passed", "modified_passed", "alternative_passed", "committee_bill_passed", "reconsidered_passed", "passed"],
    "가결": ["original_passed", "modified_passed", "alternative_passed", "committee_bill_passed", "reconsidered_passed", "passed"],
    "원안가결": ["original_passed"],
    "수정가결": ["modified_passed"],
    "대안가결": ["alternative_passed", "committee_bill_passed"],
    "철회": ["withdrawn"],
    "폐기": ["discarded", "alternative_discarded", "amended_alternative_discarded"],
    "대안반영폐기": ["alternative_discarded"],
    "부결": ["rejected"],
    "회송": ["returned"],
    "심사미료": ["unfinished"],
}

TITLE_TAG_STOPWORDS = {
    "일부개정법률안",
    "개정법률안",
    "법률안",
    "일부개정",
    "개정",
    "관한",
    "위한",
    "등의",
    "등에",
    "관련",
    "지원",
}


SEARCH_SUFFIX_STOPWORDS = (
    "관련된",
    "관련한",
    "관련",
    "법의안",
    "법률안",
    "발의안",
    "법안",
    "법률",
)

STRATEGY_TERM_SYNONYMS = {
    "기후 피해": ["기후", "기후변화", "기후위기", "재난", "피해", "지원", "복구", "농업재해", "수산"],
    "농수산업": ["농수산업", "농업", "농촌", "농어촌", "수산", "수산업", "어업", "식품산업", "스마트농업"],
    "기업 지원": ["기업", "중소기업", "벤처", "벤처기업", "창업", "스타트업", "소상공인", "사업자", "지원"],
    "청년": ["청년", "청년창업", "청년고용", "청년일자리"],
    "일자리": ["일자리", "고용", "취업", "채용", "근로"],
}

CLARIFY_INTENTS = {"chitchat", "nonsense", "too_broad"}


def _expand_search_token(token):
    normalized = token.strip().lower()
    if not normalized:
        return []

    variants = [normalized]
    for suffix in SEARCH_SUFFIX_STOPWORDS:
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            variants.append(normalized[: -len(suffix)])

    expanded = []
    for variant in variants:
        if len(variant) < 2 or variant in SEARCH_STOPWORDS:
            continue
        if variant not in expanded:
            expanded.append(variant)
    return expanded


def _as_text_list(value, limit=8):
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[,/|]+", value)
    elif isinstance(value, (list, tuple, set)):
        parts = value
    else:
        parts = [value]

    result = []
    for item in parts:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _expand_strategy_terms(values):
    terms = []
    for value in _as_text_list(values, limit=12):
        lowered = value.lower()
        if lowered and len(lowered) >= 2 and lowered not in terms:
            terms.append(lowered)
        for token in re.findall(r"[가-힣A-Za-z0-9]+", value):
            for expanded in _expand_search_token(token):
                if expanded not in terms:
                    terms.append(expanded)

        for key, synonyms in STRATEGY_TERM_SYNONYMS.items():
            key_lower = key.lower()
            if key_lower in lowered or lowered in key_lower:
                for synonym in synonyms:
                    normalized = synonym.lower()
                    if normalized not in terms:
                        terms.append(normalized)
    return terms


def _should_use_llm_strategy(query):
    tokens = re.findall(r"[가-힣A-Za-z0-9]+", query)
    complex_markers = (
        "인데",
        "했는데",
        "피해",
        "계약",
        "조언",
        "추천",
        "어떻게",
        "뭘",
        "어떤",
        "가능",
    )
    return (
        len(query) >= 28
        or len(tokens) >= 5
        or any(marker in query for marker in complex_markers)
    )


def _clamp_confidence(value, default=0.6):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def _terms_to_topics(values):
    text = " ".join(_as_text_list(values, limit=30)).lower()
    topics = []
    for topic, terms in SEARCH_TOPIC_SYNONYMS.items():
        if any(term.lower() in text for term in terms):
            topics.append(topic)
    return topics


def _promote_rule_strategy(query, analysis):
    if not _should_use_llm_strategy(query):
        return analysis

    topics = analysis.get("topics") or []
    must_have = []
    nice_to_have = []

    if "기후" in topics:
        must_have.append("기후 피해" if any(term in query for term in ("피해", "재난", "복구")) else "기후")
    if "농수산업" in topics:
        must_have.append("농수산업")
    if "기업" in topics:
        must_have.append("기업 지원")

    for topic in ("청년", "일자리", "노동", "복지"):
        if topic in topics and topic not in nice_to_have:
            nice_to_have.append(topic)

    if not must_have:
        for topic in topics[:3]:
            if topic not in {"복지"}:
                must_have.append(topic)
            if len(must_have) >= 2:
                break

    if not must_have:
        return analysis

    keyword_terms = _expand_strategy_terms([*must_have, *nice_to_have])
    merged_keywords = []
    for keyword in [*keyword_terms, *analysis.get("keywords", [])]:
        if keyword and keyword not in merged_keywords:
            merged_keywords.append(keyword)

    analysis.update({
        "mustHave": must_have[:4],
        "mustHaveTerms": [_expand_strategy_terms([term]) for term in must_have[:4]],
        "niceToHave": nice_to_have[:5],
        "niceToHaveTerms": _expand_strategy_terms(nice_to_have[:5]),
        "exclude": analysis.get("exclude") or [],
        "excludeTerms": analysis.get("excludeTerms") or [],
        "keywords": merged_keywords[:28],
        "confidence": analysis.get("confidence") or 0.58,
        "source": "rules_strategy",
    })
    return analysis


def _build_search_analysis(query):
    analysis = _analyze_search_query(query)
    analysis["source"] = "rules"

    if not _should_use_llm_strategy(query):
        return analysis

    strategy = analyze_user_query(query)
    if not isinstance(strategy, dict):
        return _promote_rule_strategy(query, analysis)

    intent = str(strategy.get("intent") or analysis.get("intent") or "search").strip().lower()
    confidence = _clamp_confidence(strategy.get("confidence"), default=0.55)
    must_have = _as_text_list(strategy.get("must_have"), limit=4)
    nice_to_have = _as_text_list(strategy.get("nice_to_have"), limit=5)
    exclude = _as_text_list(strategy.get("exclude"), limit=5)
    strategy_keywords = _as_text_list(strategy.get("keywords"), limit=8)
    search_query = str(strategy.get("search_query") or "").strip()

    keyword_terms = _expand_strategy_terms([search_query, *strategy_keywords, *must_have, *nice_to_have])
    merged_keywords = []
    for keyword in [*keyword_terms, *analysis.get("keywords", [])]:
        if keyword and keyword not in merged_keywords:
            merged_keywords.append(keyword)

    topic_values = [search_query, *strategy_keywords, *must_have, *nice_to_have]
    topics = []
    for topic in [*_terms_to_topics(topic_values), *analysis.get("topics", [])]:
        if topic not in topics:
            topics.append(topic)

    risk_level = str(strategy.get("risk_level") or analysis.get("risk_level") or "Low").strip()
    if intent == "unsafe":
        risk_level = "High"

    clarification_needed = bool(strategy.get("clarification_needed"))
    if intent in CLARIFY_INTENTS and confidence < 0.55:
        clarification_needed = True
    if confidence < 0.35 and not must_have:
        clarification_needed = True

    analysis.update({
        "summary": strategy.get("summary") or analysis.get("summary"),
        "issue": strategy.get("issue") or strategy.get("summary") or analysis.get("issue"),
        "searchQuery": search_query,
        "keywords": merged_keywords[:28],
        "strategyKeywords": strategy_keywords,
        "mustHave": must_have,
        "mustHaveTerms": [_expand_strategy_terms([term]) for term in must_have],
        "niceToHave": nice_to_have,
        "niceToHaveTerms": _expand_strategy_terms(nice_to_have),
        "exclude": exclude,
        "excludeTerms": _expand_strategy_terms(exclude),
        "topics": topics,
        "intent": intent if intent else analysis.get("intent"),
        "risk_level": risk_level if risk_level in {"High", "Medium", "Low"} else analysis.get("risk_level"),
        "confidence": confidence,
        "clarificationNeeded": clarification_needed,
        "clarificationQuestion": strategy.get("clarification_question") or "",
        "source": "llm_strategy",
    })
    return analysis


def _analyze_search_query(query):
    tokens = re.findall(r"[가-힣A-Za-z0-9]+", query)
    query_lower = query.lower()
    keywords = []
    for token in tokens:
        for normalized in _expand_search_token(token):
            if normalized not in keywords:
                keywords.append(normalized)
    topics = []
    expanded_keywords = list(keywords)
    for topic, terms in SEARCH_TOPIC_SYNONYMS.items():
        if any(term.lower() in query_lower for term in terms):
            topics.append(topic)
            for term in terms:
                normalized = term.lower()
                if normalized not in expanded_keywords:
                    expanded_keywords.append(normalized)

    stages = []
    for term, stage in SEARCH_STAGE_TERMS.items():
        if term.lower() in query_lower and stage not in stages:
            stages.append(stage)

    result_statuses = []
    for term, statuses in SEARCH_RESULT_TERMS.items():
        if term.lower() in query_lower:
            for result_status in statuses:
                if result_status not in result_statuses:
                    result_statuses.append(result_status)

    dangerous = any(term in query.lower() for term in DANGEROUS_SEARCH_TERMS)
    intent = "existence_check" if any(
        term in query_lower
        for term in ("있어", "있나요", "있냐", "있을까", "된게", "된 게", "이미", "여부")
    ) else "search"
    return {
        "summary": f"'{query}' 관련 법안 검색",
        "issue": "검색어와 관련된 국회 발의안 확인",
        "keywords": expanded_keywords[:20],
        "rawKeywords": keywords[:8],
        "topics": topics,
        "filters": {
            "stage": stages,
            "resultStatus": result_statuses,
        },
        "intent": intent,
        "risk_level": "High" if dangerous else "Low",
    }


def _build_search_context(bills):
    lines = []
    for bill in bills[:5]:
        categories = ", ".join(
            mapping.category.label for mapping in bill.bill_categories.all()
        )
        proposed_at = bill.proposed_at.strftime("%Y.%m.%d") if bill.proposed_at else ""
        result = bill.result_text or bill.result_status or "진행 중"
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
        lines.append(
            f"[{bill.bill_id}] {bill.title} | 분야: {categories or '미분류'} | "
            f"발의일: {proposed_at} | 단계: {bill.get_stage_display()} | 처리결과: {result} | "
            f"요약: {summary[:240]}"
        )
    return "\n".join(lines)


def _bill_search_fields(bill):
    categories = " ".join(mapping.category.label for mapping in bill.bill_categories.all())
    try:
        summary = " ".join(
            part
            for part in (
                bill.summary.summary_1,
                bill.summary.summary_2,
                bill.summary.summary_3,
                bill.summary.impact,
            )
            if part
        )
        summary_ready = True
    except BillSummary.DoesNotExist:
        summary = ""
        summary_ready = False

    title = bill.title or ""
    committee = bill.committee or ""
    result = " ".join(part for part in (bill.result_text, bill.result_status, bill.proposer) if part)
    return {
        "title": title.lower(),
        "categories": categories.lower(),
        "summary": summary.lower(),
        "committee": committee.lower(),
        "result": result.lower(),
        "all": f"{title} {categories} {summary} {committee} {result}".lower(),
        "summary_ready": summary_ready,
    }


def _matches_any(text, terms):
    return any(term and term.lower() in text for term in terms)


def _score_bill_for_search(bill, analysis):
    fields = _bill_search_fields(bill)
    exclude_terms = analysis.get("excludeTerms") or []
    if exclude_terms and _matches_any(fields["all"], exclude_terms):
        return None

    required_groups = [group for group in (analysis.get("mustHaveTerms") or []) if group]
    matched_required = 0
    score = 0.0
    for group in required_groups:
        if _matches_any(fields["all"], group):
            matched_required += 1
            score += 7.0
            if _matches_any(fields["title"], group):
                score += 4.0
            if _matches_any(fields["categories"], group):
                score += 3.0
            if _matches_any(fields["summary"], group):
                score += 2.0

    if required_groups:
        required_min = 2 if len(required_groups) >= 3 else 1
        if matched_required < required_min:
            return None
        if matched_required == len(required_groups):
            score += 4.0

    nice_terms = analysis.get("niceToHaveTerms") or []
    for term in nice_terms:
        if term in fields["title"]:
            score += 2.0
        elif term in fields["categories"] or term in fields["summary"]:
            score += 1.2
        elif term in fields["all"]:
            score += 0.6

    keywords = analysis.get("keywords") or []
    for term in keywords:
        if not term:
            continue
        if term in fields["title"]:
            score += 4.0
        elif term in fields["categories"]:
            score += 3.0
        elif term in fields["summary"]:
            score += 2.0
        elif term in fields["committee"] or term in fields["result"]:
            score += 1.0

    topics = analysis.get("topics") or []
    for topic in topics:
        topic_terms = [term.lower() for term in SEARCH_TOPIC_SYNONYMS.get(topic, [])]
        if _matches_any(fields["all"], topic_terms):
            score += 2.0

    if fields["summary_ready"]:
        score += 0.5

    if not required_groups and score <= 0:
        return None
    if score < 3.0:
        return None
    return score


def _search_bills_by_analysis(analysis: dict, limit: int = 5) -> list:
    """사용자 질문 분석 결과를 DB 필터와 점수 기반 검색으로 변환합니다."""
    keywords = analysis.get("keywords", [])
    filters = analysis.get("filters") or {}
    stages = filters.get("stage") or []
    result_statuses = filters.get("resultStatus") or []
    must_terms = [term for group in (analysis.get("mustHaveTerms") or []) for term in group]
    nice_terms = analysis.get("niceToHaveTerms") or []
    if not keywords and not must_terms and not nice_terms and not stages and not result_statuses:
        return []

    qs = (
        Bill.objects
        .select_related("summary")
        .prefetch_related("bill_categories__category", "similar_bills", "processing_tasks")
        .annotate(
            summary_sort=Case(
                When(summary__isnull=False, then=0),
                default=1,
                output_field=IntegerField(),
            )
        )
    )

    if stages:
        qs = qs.filter(stage__in=stages)
    if result_statuses:
        qs = qs.filter(result_status__in=result_statuses)

    query = Q()
    candidate_terms = []
    for term in [*must_terms, *nice_terms, *keywords]:
        if term and term not in candidate_terms:
            candidate_terms.append(term)

    for kw in candidate_terms:
        if kw:
            query |= (
                Q(title__icontains=kw)
                | Q(committee__icontains=kw)
                | Q(summary__summary_1__icontains=kw)
                | Q(summary__summary_2__icontains=kw)
                | Q(summary__summary_3__icontains=kw)
                | Q(summary__impact__icontains=kw)
                | Q(bill_categories__category__label__icontains=kw)
                | Q(result_text__icontains=kw)
                | Q(proposer__icontains=kw)
            )
    if query:
        qs = qs.filter(query)

    candidates = list(qs.order_by("summary_sort", "-proposed_at").distinct()[:250])
    scored = []
    for bill in candidates:
        score = _score_bill_for_search(bill, analysis)
        if score is None:
            continue
        proposed_value = int(bill.proposed_at.strftime("%Y%m%d")) if bill.proposed_at else 0
        scored.append((score, proposed_value, bill))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [bill for _, __, bill in scored[:limit]]


def _compose_db_search_answer(query: str, analysis: dict, bills: list) -> str:
    """검색 1차 응답과 AI 장애 fallback에 쓰는 DB 근거 답변."""
    if not bills:
        return "질문 조건에 맞는 법안을 찾지 못했습니다. 표현을 조금 바꾸거나 더 넓은 주제어로 다시 검색해 보세요."

    count = len(bills)
    titles = ", ".join(bill.title for bill in bills[:2])
    filters = analysis.get("filters") or {}
    stage_filter = filters.get("stage") or []
    if analysis.get("intent") == "existence_check":
        if stage_filter:
            stage_names = ", ".join(dict(Bill.STAGE_CHOICES).get(stage, stage) for stage in stage_filter)
            return f"{stage_names} 단계에서 질문 내용과 겹치는 법안 {count}건을 찾았습니다. 대표적으로 {titles}이 있습니다."
        return f"질문 내용과 겹치는 법안 {count}건을 찾았습니다. 대표적으로 {titles}이 있습니다."
    return f"질문과 관련성이 있는 법안 {count}건을 찾았습니다. 대표 결과는 {titles}입니다."


def _compose_clarification_answer(analysis: dict) -> str:
    question = str(analysis.get("clarificationQuestion") or "").strip()
    if question:
        return question
    must_have = analysis.get("mustHave") or []
    if must_have:
        choices = ", ".join(must_have[:3])
        return f"질문에 여러 주제가 섞여 있어요. {choices} 중 어떤 축을 먼저 볼지 조금만 좁혀 주세요."
    return "질문 의도를 바로 법안 검색으로 연결하기 어렵습니다. 궁금한 분야나 상황을 한 문장으로 조금 더 구체화해 주세요."


def _build_search_display_tags(analysis: dict, bills: list) -> list[str]:
    """화면 노출용 검색 태그를 질문 토큰 대신 결과 맥락에서 만듭니다."""
    tags = []

    def add_tag(value):
        tag = str(value or "").strip()
        if not tag or len(tag) < 2 or tag in tags:
            return
        tags.append(tag)

    category_counts = Counter()
    for bill in bills:
        for mapping in bill.bill_categories.all():
            category_counts[mapping.category.label] += 1
    for label, _ in category_counts.most_common(4):
        add_tag(label)

    for topic in analysis.get("topics") or []:
        add_tag(topic)

    stage_labels = dict(Bill.STAGE_CHOICES)
    for stage in (analysis.get("filters") or {}).get("stage") or []:
        add_tag(stage_labels.get(stage, stage))

    result_labels = {
        "original_passed": "원안가결",
        "modified_passed": "수정가결",
        "alternative_passed": "대안가결",
        "committee_bill_passed": "위원회안가결",
        "reconsidered_passed": "번안가결",
        "passed": "가결",
        "withdrawn": "철회",
        "discarded": "폐기",
        "alternative_discarded": "대안반영폐기",
        "amended_alternative_discarded": "수정안반영폐기",
        "rejected": "부결",
        "returned": "회송",
        "unfinished": "심사미료",
    }
    for status_value in (analysis.get("filters") or {}).get("resultStatus") or []:
        add_tag(result_labels.get(status_value, status_value))

    title_terms = Counter()
    for bill in bills:
        cleaned_title = re.sub(r"(일부개정법률안|개정법률안|법률안)", " ", bill.title)
        for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", cleaned_title):
            if token in TITLE_TAG_STOPWORDS:
                continue
            title_terms[token] += 1
    for token, _ in title_terms.most_common(6):
        add_tag(token)
        if len(tags) >= 6:
            break

    return tags[:6]


def _search_bills_by_keywords_for_search(keywords: list) -> list:
    """이전 테스트와 내부 호출 호환을 위한 키워드 검색 wrapper입니다."""
    return _search_bills_by_analysis({"keywords": keywords, "filters": {}})


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
