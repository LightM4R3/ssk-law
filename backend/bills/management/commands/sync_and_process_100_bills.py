import time
import datetime
import requests
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from bills.models import Bill, Category, BillCategory, BillSummary
from services import ollama

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Syncs 100 bills from the Assembly APIs and processes them with Ollama LLM."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pages",
            type=int,
            default=10,
            help="Number of pages to sync from general Assembly API (default: 10, yields 100 bills)",
        )
        parser.add_argument(
            "--limit-llm",
            type=int,
            default=100,
            help="Maximum number of bills to process with LLM in this run to control execution time (default: 100)",
        )

    def handle(self, *args, **options):
        pages = options["pages"]
        limit_llm = options["limit_llm"]
        api_key = getattr(settings, "ASSEMBLY_API_KEY", "7ebbc9b78224446d89af859b2117e88e")

        self.stdout.write(self.style.WARNING(f"=== STEP 1: Syncing {pages * 10} general bills from API ==="))
        
        # 1. Ensure categories exist
        categories_map = self._ensure_categories()

        # 2. Call General Assembly API
        base_url = "https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn"
        synced_count = 0

        for page in range(1, pages + 1):
            url = f"{base_url}?KEY={api_key}&Type=json&pIndex={page}&pSize=10&AGE=22"
            self.stdout.write(f"Fetching general bills page {page} / {pages}...")

            try:
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to fetch bills from API: {e}"))
                break

            bill_data = data.get("nzmimeepazxkubdpn", [])
            if len(bill_data) <= 1 or "row" not in bill_data[1]:
                self.stdout.write("No rows found in response.")
                break

            raw_bills = bill_data[1]["row"]
            for raw in raw_bills:
                bill_no = raw.get("BILL_NO")
                if not bill_no:
                    continue

                title = raw.get("BILL_NAME", "제목 없음")
                proposer = raw.get("PROPOSER", "발의자 정보 없음")
                committee = raw.get("COMMITTEE", "") or raw.get("COMMITTEE_NAME", "") or "미정"
                detail_link = raw.get("DETAIL_LINK", "")
                
                # Parse date
                propose_dt_str = raw.get("PROPOSE_DT", "")
                try:
                    proposed_at = datetime.date.fromisoformat(propose_dt_str)
                except (ValueError, TypeError):
                    proposed_at = datetime.date.today()

                # Stage normalization
                stage_label = raw.get("PROC_RESULT", "") or "발의"
                stage = self._normalize_stage(stage_label)

                # Prevent stage downgrade
                try:
                    existing_bill = Bill.objects.get(bill_id=bill_no)
                    existing_stage = existing_bill.stage
                    stage_order = {"proposed": 1, "committee": 2, "plenary": 3, "passed": 4}
                    if stage_order.get(stage, 1) < stage_order.get(existing_stage, 1):
                        stage = existing_stage
                except Bill.DoesNotExist:
                    pass

                # Save or Update Bill
                bill, created = Bill.objects.update_or_create(
                    bill_id=bill_no,
                    defaults={
                        "bill_no": bill_no,
                        "title": title,
                        "proposer": proposer,
                        "committee": committee,
                        "stage": stage,
                        "proposed_at": proposed_at,
                        "detail_link": detail_link,
                        "age": 22,
                        "synced_at": timezone.now(),
                    }
                )
                
                if created:
                    # Apply fallback categories first
                    self._map_categories(bill, committee, categories_map)
                
                synced_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully synced {synced_count} bills."))

        # 3. Sync Judiciary stages (100 items)
        self.stdout.write(self.style.WARNING("\n=== STEP 2: Syncing 100 Judiciary Committee (법사위) bills ==="))
        self._sync_committee_stages(api_key)

        # 4. Sync Plenary stages (100 items)
        self.stdout.write(self.style.WARNING("\n=== STEP 3: Syncing 100 Plenary (본회의) bills ==="))
        self._sync_plenary_stages(api_key)

        # 5. Process AI Summaries via LLM for the newly synced/unsummarized bills
        self.stdout.write(self.style.WARNING(f"\n=== STEP 4: Processing AI Summaries (Limit: {limit_llm}) ==="))
        self._process_llm_summaries(api_key, categories_map, limit_llm)

    def _ensure_categories(self):
        categories_seed = [
            ("labor", "노동", 1),
            ("welfare", "복지", 2),
            ("housing", "주거", 3),
            ("economy", "경제", 4),
            ("education", "교육", 5),
            ("env", "환경 · 기후", 6),
            ("digital", "디지털", 7),
            ("health", "보건", 8),
            ("safety", "생활안전", 9),
        ]
        cat_map = {}
        for slug, label, order in categories_seed:
            cat, _ = Category.objects.update_or_create(
                slug=slug, defaults={"label": label, "sort_order": order}
            )
            cat_map[slug] = cat
        return cat_map

    def _normalize_stage(self, stage_str):
        s = stage_str.strip()
        if "통과" in s or "공포" in s or "가결" in s:
            return "passed"
        elif "본회의" in s:
            return "plenary"
        elif "위원회" in s or "심사" in s:
            return "committee"
        return "proposed"

    def _map_categories(self, bill, committee, categories_map):
        BillCategory.objects.filter(bill=bill).delete()
        mapped_slugs = []
        if "환경" in committee or "노동" in committee:
            mapped_slugs.append("labor")
            mapped_slugs.append("env")
        if "보건" in committee or "복지" in committee or "여성" in committee or "가족" in committee:
            mapped_slugs.append("welfare")
            mapped_slugs.append("health")
        if "국토" in committee or "교통" in committee:
            mapped_slugs.append("housing")
        if "재정" in committee or "경제" in committee or "정무" in committee or "산업" in committee or "통상" in committee or "벤처" in committee:
            mapped_slugs.append("economy")
        if "교육" in committee or "문화" in committee or "체육" in committee or "관광" in committee:
            mapped_slugs.append("education")
        if "과학" in committee or "기술" in committee or "정보" in committee or "방송" in committee or "통신" in committee:
            mapped_slugs.append("digital")
        if "행정" in committee or "안전" in committee or "국방" in committee or "외교" in committee or "통일" in committee:
            mapped_slugs.append("safety")

        if not mapped_slugs:
            mapped_slugs.append("safety")

        for i, slug in enumerate(mapped_slugs):
            if slug in categories_map:
                BillCategory.objects.create(
                    bill=bill,
                    category=categories_map[slug],
                    is_primary=(i == 0)
                )

    def _sync_committee_stages(self, api_key):
        url = "https://open.assembly.go.kr/portal/openapi/TVBPMBILL11"
        params = {
            "KEY": api_key,
            "Type": "json",
            "pIndex": 1,
            "pSize": 100,  # 100 items
            "AGE": 22
        }
        
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch committee bills: {e}"))
            return

        bill_data = data.get("TVBPMBILL11", [])
        if len(bill_data) <= 1 or "row" not in bill_data[1]:
            self.stdout.write("No committee rows found.")
            return

        raw_bills = bill_data[1]["row"]
        updated_count = 0
        created_count = 0
        categories_map = self._ensure_categories()
        
        for raw in raw_bills:
            bill_no = raw.get("BILL_NO")
            if not bill_no:
                continue
                
            law_proc_result = raw.get("LAW_PROC_RESULT_CD", "") or ""
            law_proc_dt = raw.get("LAW_PROC_DT", "")
            
            if law_proc_dt or law_proc_result:
                try:
                    bill = Bill.objects.get(bill_no=bill_no)
                    existing_stage = bill.stage
                    stage_order = {"proposed": 1, "committee": 2, "plenary": 3, "passed": 4}
                    if stage_order.get("plenary", 3) > stage_order.get(existing_stage, 1):
                        bill.stage = "plenary"
                        bill.save()
                        self.stdout.write(f"  [Judiciary Stage Update] Bill {bill_no} stage advanced to plenary.")
                        updated_count += 1
                except Bill.DoesNotExist:
                    bill_id = raw.get("BILL_ID") or bill_no
                    title = raw.get("BILL_NAME", "제목 없음")
                    proposer = raw.get("PROPOSER", "발의자 정보 없음")
                    committee = raw.get("CURR_COMMITTEE", "") or "법제사법위원회"
                    detail_link = raw.get("LINK_URL", "")
                    
                    propose_dt_str = raw.get("PROPOSE_DT", "")
                    try:
                        proposed_at = datetime.date.fromisoformat(propose_dt_str)
                    except (ValueError, TypeError):
                        proposed_at = datetime.date.today()
                        
                    bill = Bill.objects.create(
                        bill_id=bill_id,
                        bill_no=bill_no,
                        title=title,
                        proposer=proposer,
                        committee=committee,
                        stage="plenary",
                        proposed_at=proposed_at,
                        detail_link=detail_link,
                        age=22,
                        synced_at=timezone.now()
                    )
                    self._map_categories(bill, committee, categories_map)
                    self.stdout.write(f"  [Judiciary Stage Created] New Bill {bill_no} created with stage plenary.")
                    created_count += 1
                    
        self.stdout.write(self.style.SUCCESS(f"Finished Judiciary Committee sync. Updated {updated_count}, Created {created_count} bills."))

    def _sync_plenary_stages(self, api_key):
        url = "https://open.assembly.go.kr/portal/openapi/nwbpacrgavhjryiph"
        params = {
            "KEY": api_key,
            "Type": "json",
            "pIndex": 1,
            "pSize": 100,  # 100 items
            "AGE": 22
        }
        
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch plenary bills: {e}"))
            return

        bill_data = data.get("nwbpacrgavhjryiph", [])
        if len(bill_data) <= 1 or "row" not in bill_data[1]:
            self.stdout.write("No plenary rows found.")
            return

        raw_bills = bill_data[1]["row"]
        updated_count = 0
        created_count = 0
        categories_map = self._ensure_categories()
        
        for raw in raw_bills:
            bill_no = raw.get("BILL_NO")
            if not bill_no:
                continue
                
            proc_result = raw.get("PROC_RESULT_CD", "") or ""
            
            if "가결" in proc_result or proc_result in ["수정가결", "원안가결"]:
                try:
                    bill = Bill.objects.get(bill_no=bill_no)
                    existing_stage = bill.stage
                    stage_order = {"proposed": 1, "committee": 2, "plenary": 3, "passed": 4}
                    if stage_order.get("passed", 4) > stage_order.get(existing_stage, 1):
                        bill.stage = "passed"
                        bill.save()
                        self.stdout.write(f"  [Plenary Stage Update] Bill {bill_no} stage advanced to passed.")
                        updated_count += 1
                except Bill.DoesNotExist:
                    bill_id = raw.get("BILL_ID") or bill_no
                    raw_title = raw.get("BILL_NM", "제목 없음")
                    title = raw_title.split("(")[0].strip() if "(" in raw_title else raw_title
                    
                    proposer = raw.get("PROPOSER", "발의자 정보 없음")
                    committee = raw.get("COMMITTEE_NM", "") or "본회의"
                    detail_link = raw.get("LINK_URL", "")
                    
                    propose_dt_str = raw.get("PROPOSE_DT", "")
                    try:
                        proposed_at = datetime.date.fromisoformat(propose_dt_str)
                    except (ValueError, TypeError):
                        proposed_at = datetime.date.today()
                        
                    bill = Bill.objects.create(
                        bill_id=bill_id,
                        bill_no=bill_no,
                        title=title,
                        proposer=proposer,
                        committee=committee,
                        stage="passed",
                        proposed_at=proposed_at,
                        detail_link=detail_link,
                        age=22,
                        synced_at=timezone.now()
                    )
                    self._map_categories(bill, committee, categories_map)
                    self.stdout.write(f"  [Plenary Stage Created] New Bill {bill_no} created with stage passed.")
                    created_count += 1
                    
        self.stdout.write(self.style.SUCCESS(f"Finished Plenary sync. Updated {updated_count}, Created {created_count} bills."))

    def _process_llm_summaries(self, api_key, categories_map, limit):
        # Find bills without summaries
        unsummarized = Bill.objects.filter(summary__isnull=True).order_by("-proposed_at")
        total = unsummarized.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS("All bills already have summaries!"))
            return

        process_count = min(total, limit)
        self.stdout.write(self.style.WARNING(f"Found {total} unsummarized bill(s). Processing first {process_count} with Ollama..."))

        success_count = 0
        endpoint = "BPMBILLSUMMARY"

        for index, bill in enumerate(unsummarized[:process_count], 1):
            bill_id = bill.bill_id
            title = bill.title
            proposer = bill.proposer
            committee = bill.committee

            self.stdout.write(f"\n[{index}/{process_count}] Processing Bill {bill_id}: {title[:40]}...")
            start_time = time.time()

            # 1. Fetch text from BPMBILLSUMMARY API
            bill_content = ""
            detail_url = f"https://open.assembly.go.kr/portal/openapi/{endpoint}?KEY={api_key}&Type=json&pIndex=1&pSize=1&BILL_NO={bill_id}"
            
            try:
                resp = requests.get(detail_url, timeout=10)
                resp.raise_for_status()
                detail_data = resp.json()

                if endpoint in detail_data and len(detail_data[endpoint]) > 1 and "row" in detail_data[endpoint][1]:
                    raw_summary = detail_data[endpoint][1]["row"][0].get("SUMMARY")
                    bill_content = raw_summary.strip() if raw_summary else ""
                    self.stdout.write(self.style.SUCCESS(f"  -> Retrieved detailed content ({len(bill_content)} chars)"))
                else:
                    self.stdout.write("  -> No detailed content in Assembly response (using title only)")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  -> Failed to fetch detail content: {e}"))

            # 2. Call Ollama model
            self.stdout.write("  -> Generating AI Summary with Ollama...")
            summary_dict = ollama.summarize_bill(title, proposer, committee, bill_content)

            if summary_dict:
                # Save Summary (using update_or_create to prevent UNIQUE constraint failure)
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

                # Map LLM categories
                llm_categories = summary_dict.get("categories", [])
                valid_llm_categories = [slug for slug in llm_categories if slug in categories_map]
                
                if valid_llm_categories:
                    BillCategory.objects.filter(bill=bill).delete()
                    for i, slug in enumerate(valid_llm_categories):
                        BillCategory.objects.create(
                            bill=bill,
                            category=categories_map[slug],
                            is_primary=(i == 0)
                        )
                    self.stdout.write(self.style.SUCCESS(f"  -> Mapped LLM categories: {valid_llm_categories}"))

                elapsed = time.time() - start_time
                self.stdout.write(self.style.SUCCESS(f"  -> Finished in {elapsed:.2f} seconds"))
                success_count += 1
            else:
                self.stdout.write(self.style.ERROR("  -> AI Summary generation failed"))

        self.stdout.write(self.style.SUCCESS(f"\nOllama Processing Finished: processed {success_count} / {process_count} bills."))
