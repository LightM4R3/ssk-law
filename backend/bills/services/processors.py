from django.conf import settings
from django.db import transaction

from bills.models import BillCategory, BillSummary, Category
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

