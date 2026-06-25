import math
import re
from collections import Counter
from datetime import date

from django.db import transaction

from bills.models import Bill, BillSummary, SimilarBill


SIMILARITY_METHOD = "report_weighted_v1"
TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]{2,}")

# 발표 보고서의 final_ensemble_title_heavy_balanced 중
# weighted_field_title_sbert_balanced 항목을 로컬 keyword cache에 맞게 근사한다.
FIELD_WEIGHTS = {
    "title": 0.30,
    "full": 0.10,
    "current": 0.15,
    "problem": 0.15,
    "proposal": 0.15,
    "article": 0.15,
}
CATEGORY_OVERLAP_BONUS = 0.06
CATEGORY_EXTRA_BONUS = 0.02
COMMITTEE_BONUS = 0.04

STOPWORDS = {
    "일부개정법률안",
    "개정법률안",
    "법률안",
    "법의안",
    "발의안",
    "법안",
    "법률",
    "일부개정",
    "개정",
    "관한",
    "관련",
    "관련된",
    "관련한",
    "대한",
    "위한",
    "제안이유",
    "주요내용",
    "현행법",
    "하려는",
    "하고자",
    "있음",
    "하는",
    "하도록",
    "이에",
    "또는",
}
TOKEN_SUFFIXES = (
    "일부개정법률안",
    "개정법률안",
    "법률안",
    "법의안",
    "발의안",
    "법안",
    "일부개정",
    "관련된",
    "관련한",
    "관련",
)


def ensure_similar_bills(bill, limit=5, refresh=False):
    """Return cached similar bills, building a local weighted cache if needed."""
    cached = list(
        bill.similar_bills
        .filter(method=SIMILARITY_METHOD)
        .select_related("target_bill")
        .order_by("rank", "-score")[:limit]
    )
    if cached and not refresh:
        return cached

    matches = build_keyword_similarities(bill, limit=limit)
    with transaction.atomic():
        SimilarBill.objects.filter(source_bill=bill).delete()
        SimilarBill.objects.bulk_create(
            [
                SimilarBill(
                    source_bill=bill,
                    target_bill=target,
                    title=target.title,
                    date=target.proposed_at.strftime("%Y.%m.%d") if target.proposed_at else "",
                    stage_label=target.get_stage_display(),
                    score=score,
                    rank=index,
                    method=SIMILARITY_METHOD,
                )
                for index, (target, score) in enumerate(matches, start=1)
            ]
        )

    return list(
        SimilarBill.objects
        .filter(source_bill=bill, method=SIMILARITY_METHOD)
        .select_related("target_bill")
        .order_by("rank", "-score")[:limit]
    )


def build_keyword_similarities(source_bill, limit=5):
    source_vectors = build_bill_field_vectors(source_bill)
    source_categories = category_slugs(source_bill)
    if not any(source_vectors.values()):
        return []

    candidates = (
        Bill.objects
        .exclude(pk=source_bill.pk)
        .select_related("summary")
        .prefetch_related("bill_categories__category")
    )
    scored = []
    for candidate in candidates.iterator(chunk_size=200):
        score = weighted_field_score(source_vectors, build_bill_field_vectors(candidate))
        if score <= 0:
            continue

        overlap = source_categories & category_slugs(candidate)
        if overlap:
            score += CATEGORY_OVERLAP_BONUS + (CATEGORY_EXTRA_BONUS * min(len(overlap) - 1, 2))
        if source_bill.committee and source_bill.committee == candidate.committee:
            score += COMMITTEE_BONUS

        scored.append((candidate, min(score, 1.0)))

    scored.sort(key=lambda item: (item[1], item[0].proposed_at or date.min), reverse=True)
    return scored[:limit]


def build_bill_field_vectors(bill):
    summary = get_summary(bill)
    categories = " ".join(mapping.category.label for mapping in bill.bill_categories.all())
    current = " ".join(
        part
        for part in (
            bill.committee,
            categories,
            bill.get_stage_display(),
            bill.result_text,
        )
        if part
    )
    problem = summary.summary_1 if summary else ""
    proposal = " ".join(
        part
        for part in (
            summary.summary_2 if summary else "",
            summary.summary_3 if summary else "",
        )
        if part
    )
    article = " ".join(
        part
        for part in (
            summary.impact if summary else "",
            bill.result_text,
        )
        if part
    )
    full = " ".join(
        part
        for part in (
            bill.title,
            current,
            problem,
            proposal,
            article,
        )
        if part
    )

    return {
        "title": vectorize(bill.title),
        "full": vectorize(full),
        "current": vectorize(current),
        "problem": vectorize(problem),
        "proposal": vectorize(proposal),
        "article": vectorize(article),
    }


def build_bill_vector(bill):
    vector = Counter()
    for field, field_vector in build_bill_field_vectors(bill).items():
        weight = FIELD_WEIGHTS.get(field, 0)
        for token, value in field_vector.items():
            vector[token] += value * weight
    return vector


def get_summary(bill):
    try:
        return bill.summary
    except BillSummary.DoesNotExist:
        return None


def weighted_field_score(left_vectors, right_vectors):
    score = 0
    for field, weight in FIELD_WEIGHTS.items():
        score += weight * cosine(left_vectors.get(field), right_vectors.get(field))
    return score


def vectorize(text):
    vector = Counter()
    add_tokens(vector, text)
    return vector


def add_tokens(vector, text, weight=1.0):
    for token in TOKEN_RE.findall(text or ""):
        normalized = normalize_token(token)
        if normalized and normalized not in STOPWORDS:
            vector[normalized] += weight


def normalize_token(token):
    token = token.strip().lower()
    for suffix in TOKEN_SUFFIXES:
        if token.endswith(suffix) and len(token) > len(suffix):
            token = token[: -len(suffix)]
            break
    return token


def category_slugs(bill):
    return {mapping.category.slug for mapping in bill.bill_categories.all()}


def cosine(left, right):
    if not left or not right:
        return 0
    common = set(left) & set(right)
    dot = sum(left[token] * right[token] for token in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0
    return dot / (left_norm * right_norm)
