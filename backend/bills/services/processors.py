from django.conf import settings
from django.db import transaction
from django.utils.module_loading import import_string

from bills.models import Bill, BillCategory, BillSummary, Category, SimilarBill
from bills.services.assembly import AssemblyAPIClient
from bills.services.processing import BillProcessor
from services import ollama


class SummaryProcessor(BillProcessor):
    key = "summary"
    version = "v1"
    dependencies = ()

    def __init__(self, client=None):
        self.client = client or AssemblyAPIClient(timeout=10)

    def process(self, bill):
        content = self.client.fetch_bill_content(bill.bill_no)
        result = ollama.summarize_bill(
            bill.title,
            bill.proposer,
            bill.committee,
            content,
        )
        summary, categories = self._validate(result)

        category_map = {
            category.slug: category
            for category in Category.objects.filter(slug__in=categories)
        }
        if len(category_map) != len(categories):
            raise ValueError("AI returned a category that does not exist in the database")

        with transaction.atomic():
            BillSummary.objects.update_or_create(
                bill=bill,
                defaults={
                    **summary,
                    "sentiment": 0,
                    "model_name": settings.OLLAMA_MODEL,
                },
            )
            BillCategory.objects.filter(bill=bill).delete()
            BillCategory.objects.bulk_create(
                [
                    BillCategory(
                        bill=bill,
                        category=category_map[slug],
                        is_primary=index == 0,
                    )
                    for index, slug in enumerate(categories)
                ]
            )

    @staticmethod
    def _validate(result):
        if not isinstance(result, dict):
            raise ValueError("AI summary response is empty or is not a JSON object")
        summary = {
            key: str(result.get(key) or "").strip()
            for key in ("summary_1", "summary_2", "summary_3")
        }
        if not all(summary.values()):
            raise ValueError("AI response must contain three non-empty summary lines")
        summary["impact"] = str(result.get("impact") or "").strip()

        raw_categories = result.get("categories")
        if not isinstance(raw_categories, list):
            raise ValueError("AI response categories must be a list")
        allowed = {"labor", "welfare", "housing", "economy", "education", "env", "digital", "health", "safety"}
        categories = list(dict.fromkeys(str(value) for value in raw_categories if value in allowed))
        if not 1 <= len(categories) <= 2:
            raise ValueError("AI response must contain one or two valid categories")
        return summary, categories


class SimilarityProcessor(BillProcessor):
    """Optional add-on processor for teammate-owned similarity logic.

    Enable it by adding this class to BILL_PROCESSORS and pointing
    BILL_SIMILARITY_PROVIDER at a callable that accepts a Bill and returns
    a list of Bill objects or dictionaries with title/date/stage fields.
    """

    key = "similarity"
    version = "v1"
    dependencies = ("summary",)

    def __init__(self, provider=None):
        self.provider = provider

    def process(self, bill):
        provider = self.provider or self._load_provider()
        matches = provider(bill)
        if matches is None:
            matches = []
        if not isinstance(matches, list):
            raise ValueError("Similarity provider must return a list")

        similar = []
        for item in matches[:10]:
            normalized = self._normalize_match(bill, item)
            if normalized:
                similar.append(SimilarBill(source_bill=bill, **normalized))

        with transaction.atomic():
            SimilarBill.objects.filter(source_bill=bill).delete()
            if similar:
                SimilarBill.objects.bulk_create(similar)

    @staticmethod
    def _load_provider():
        provider_path = getattr(settings, "BILL_SIMILARITY_PROVIDER", "")
        if not provider_path:
            raise RuntimeError("BILL_SIMILARITY_PROVIDER is not configured")
        return import_string(provider_path)

    @staticmethod
    def _normalize_match(source_bill, item):
        if isinstance(item, Bill):
            if item.pk == source_bill.pk:
                return None
            return {
                "title": item.title,
                "date": item.proposed_at.strftime("%Y.%m.%d") if item.proposed_at else "",
                "stage_label": item.get_stage_display(),
            }

        if not isinstance(item, dict):
            raise ValueError("Similarity provider items must be Bill instances or dictionaries")

        title = str(item.get("title") or item.get("bill_title") or "").strip()
        if not title:
            return None
        return {
            "title": title[:500],
            "date": str(item.get("date") or item.get("proposed_at") or "")[:20],
            "stage_label": str(item.get("stage") or item.get("stage_label") or "")[:30],
        }
