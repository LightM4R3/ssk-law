import time
import requests
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from bills.models import Bill, Category, BillCategory, BillSummary
from services import ollama

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generates AI summaries and categories for bills without summaries using Assembly API and Ollama."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting AI summary processing..."))

        # 1. Get unsummarized bills
        unsummarized_bills = Bill.objects.filter(summary__isnull=True).order_by("-proposed_at")
        total = unsurm_count = unsurm_bills_count = unsummarized_bills.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS("All bills already have summaries!"))
            return

        self.stdout.write(self.style.WARNING(f"Found {total} bill(s) needing summaries."))

        # 2. Build Category Map for mapping
        categories = Category.objects.all()
        categories_map = {cat.slug: cat for cat in categories}

        api_key = getattr(settings, "ASSEMBLY_API_KEY", "7ebbc9b78224446d89af859b2117e88e")
        endpoint = "BPMBILLSUMMARY"

        success_count = 0

        for index, bill in enumerate(unsummarized_bills, 1):
            bill_id = bill.bill_id
            title = bill.title
            proposer = bill.proposer
            committee = bill.committee

            self.stdout.write(
                f"\n[{index}/{total}] Processing Bill {bill_id}: {title[:40]}..."
            )

            start_time = time.time()

            # 2.1 Fetch detailed text from BPMBILLSUMMARY API
            bill_content = ""
            detail_url = f"https://open.assembly.go.kr/portal/openapi/{endpoint}?KEY={api_key}&Type=json&pIndex=1&pSize=1&BILL_NO={bill_id}"
            
            try:
                self.stdout.write(f"  -> Fetching detailed summary from Assembly API...")
                resp = requests.get(detail_url, timeout=10)
                resp.raise_for_status()
                detail_data = resp.json()

                if endpoint in detail_data and len(detail_data[endpoint]) > 1 and "row" in detail_data[endpoint][1]:
                    raw_summary = detail_data[endpoint][1]["row"][0].get("SUMMARY")
                    bill_content = raw_summary.strip() if raw_summary else ""
                    self.stdout.write(self.style.SUCCESS(f"  -> Successfully retrieved detail content ({len(bill_content)} chars)"))
                else:
                    self.stdout.write(self.style.WARNING("  -> No detail content found in Assembly API response (falling back to title)"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  -> Failed to fetch detail content: {e} (falling back to title)"))

            # 2.2 Call Ollama Summarizer
            self.stdout.write("  -> Generating AI Summary with Ollama (this will take ~10 seconds)...")
            summary_dict = ollama.summarize_bill(title, proposer, committee, bill_content)

            if summary_dict:
                # Save AI Summary (using update_or_create to prevent UNIQUE constraint failure)
                BillSummary.objects.update_or_create(
                    bill=bill,
                    defaults={
                        "summary_1": summary_dict.get("summary_1", ""),
                        "summary_2": summary_dict.get("summary_2", ""),
                        "summary_3": summary_dict.get("summary_3", ""),
                        "impact": summary_dict.get("impact", ""),
                        "sentiment": 0,
                        "model_name": getattr(settings, "OLLAMA_MODEL", "gemma4:e4b"),
                    }
                )

                # Update Category Mapping from LLM classification
                llm_categories = summary_dict.get("categories", [])
                valid_llm_categories = [slug for slug in llm_categories if slug in categories_map]
                
                if valid_llm_categories:
                    # Clear fallback mapping and write LLM mapped categories
                    BillCategory.objects.filter(bill=bill).delete()
                    for i, slug in enumerate(valid_llm_categories):
                        BillCategory.objects.create(
                            bill=bill,
                            category=categories_map[slug],
                            is_primary=(i == 0)
                        )
                    self.stdout.write(self.style.SUCCESS(f"  -> Mapped LLM categories: {valid_llm_categories}"))

                elapsed = time.time() - start_time
                self.stdout.write(self.style.SUCCESS(f"  -> AI Summary generated successfully in {elapsed:.2f} seconds"))
                success_count += 1
            else:
                self.stdout.write(self.style.ERROR("  -> AI Summary generation failed"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nFinished! Successfully processed {success_count} / {total} bills."
            )
        )
