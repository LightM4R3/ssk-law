import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
import requests
import logging
from bills.models import Bill, Category, BillCategory, BillSummary
from services import ollama

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Syncs recent bills from the National Assembly API and generates AI summaries."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pages",
            type=int,
            default=1,
            help="Number of pages to sync from National Assembly API (default: 1)",
        )

    def handle(self, *args, **options):
        pages = options["pages"]
        self.stdout.write(self.style.WARNING(f"Starting bill sync for {pages} page(s)..."))

        # 1. Ensure categories exist in database (same as seed data)
        categories_map = self._ensure_categories()

        # 2. Call Assembly API
        api_key = getattr(settings, "ASSEMBLY_API_KEY", "7ebbc9b78224446d89af859b2117e88e")
        base_url = "https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn"

        synced_count = 0
        summarized_count = 0

        for page in range(1, pages + 1):
            url = f"{base_url}?KEY={api_key}&Type=json&pIndex={page}&pSize=10&AGE=22"
            self.stdout.write(f"Fetching page {page}...")

            try:
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to fetch bills list from API: {e}"))
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

                # Prevent downgrade: only update to a new stage if it is higher/forward
                try:
                    existing_bill = Bill.objects.get(bill_id=bill_no)
                    existing_stage = existing_bill.stage
                    stage_order = {"proposed": 1, "committee": 2, "plenary": 3, "passed": 4}
                    if stage_order.get(stage, 1) < stage_order.get(existing_stage, 1):
                        stage = existing_stage  # Keep the higher stage
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
                
                action = "Created" if created else "Updated"
                self.stdout.write(f"  [{action}] Bill {bill_no}: {title[:40]}...")
                synced_count += 1

                # 3. Fallback Mapping (임시 카테고리 매핑 설정)
                if not BillCategory.objects.filter(bill=bill).exists():
                    self.stdout.write(f"    -> Mapped categories via committee fallback: {committee}")
                    self._map_categories(bill, committee, categories_map)

        # 4. Sync Judiciary Committee and Plenary stages
        self._sync_committee_stages(api_key)
        self._sync_plenary_stages(api_key)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nFinished! Synced {synced_count} bills."
            )
        )

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
        # Delete old mappings first
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

        # Fallback to safety if nothing matches
        if not mapped_slugs:
            mapped_slugs.append("safety")

        # Create relationships
        for i, slug in enumerate(mapped_slugs):
            if slug in categories_map:
                BillCategory.objects.create(
                    bill=bill,
                    category=categories_map[slug],
                    is_primary=(i == 0)
                )

    def _sync_committee_stages(self, api_key):
        """법사위 처리 API를 호출하여 대상 법안의 단계를 plenary(본회의 상정)로 업데이트합니다."""
        url = "https://open.assembly.go.kr/portal/openapi/TVBPMBILL11"
        self.stdout.write(self.style.WARNING("Starting Judiciary Committee (법사위) stage synchronization..."))
        
        params = {
            "KEY": api_key,
            "Type": "json",
            "pIndex": 1,
            "pSize": 50,
            "AGE": 22
        }
        
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch committee bills from API: {e}"))
            return

        bill_data = data.get("TVBPMBILL11", [])
        if len(bill_data) <= 1 or "row" not in bill_data[1]:
            self.stdout.write("No committee rows found in response.")
            return

        raw_bills = bill_data[1]["row"]
        updated_count = 0
        
        for raw in raw_bills:
            bill_no = raw.get("BILL_NO")
            if not bill_no:
                continue
                
            law_proc_result = raw.get("LAW_PROC_RESULT_CD", "") or ""
            law_proc_dt = raw.get("LAW_PROC_DT", "")
            
            # 법사위에서 처리가 완료되었거나 일정이 있는 경우 plenary(본회의 상정)로 업데이트
            if law_proc_dt or law_proc_result:
                target_bills = Bill.objects.filter(bill_no=bill_no, stage__in=["proposed", "committee"])
                for bill in target_bills:
                    bill.stage = "plenary"
                    bill.save()
                    self.stdout.write(f"  [Judiciary Stage Update] Bill {bill_no} stage advanced to plenary.")
                    updated_count += 1
                    
        self.stdout.write(self.style.SUCCESS(f"Finished Judiciary Committee sync. Updated {updated_count} bills."))

    def _sync_plenary_stages(self, api_key):
        """본회의 처리 API를 호출하여 대상 법안의 단계를 passed(통과 · 공포)로 업데이트합니다."""
        url = "https://open.assembly.go.kr/portal/openapi/nwbpacrgavhjryiph"
        self.stdout.write(self.style.WARNING("Starting Plenary (본회의) stage synchronization..."))
        
        params = {
            "KEY": api_key,
            "Type": "json",
            "pIndex": 1,
            "pSize": 50,
            "AGE": 22
        }
        
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch plenary bills from API: {e}"))
            return

        bill_data = data.get("nwbpacrgavhjryiph", [])
        if len(bill_data) <= 1 or "row" not in bill_data[1]:
            self.stdout.write("No plenary rows found in response.")
            return

        raw_bills = bill_data[1]["row"]
        updated_count = 0
        
        for raw in raw_bills:
            bill_no = raw.get("BILL_NO")
            if not bill_no:
                continue
                
            proc_result = raw.get("PROC_RESULT_CD", "") or ""
            
            # 본회의 의결결과가 존재하고 가결 취지인 경우 passed로 업데이트
            if "가결" in proc_result or proc_result in ["수정가결", "원안가결"]:
                target_bills = Bill.objects.filter(bill_no=bill_no, stage__in=["proposed", "committee", "plenary"])
                for bill in target_bills:
                    bill.stage = "passed"
                    bill.save()
                    self.stdout.write(f"  [Plenary Stage Update] Bill {bill_no} stage advanced to passed.")
                    updated_count += 1
                    
        self.stdout.write(self.style.SUCCESS(f"Finished Plenary sync. Updated {updated_count} bills."))
