import datetime
from dataclasses import dataclass, field

import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from bills.models import Bill, BillCategory, Category, SyncRun


CATEGORY_SEED = [
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

STAGE_ORDER = {"proposed": 1, "committee": 2, "plenary": 3, "passed": 4}


class AssemblyAPIError(RuntimeError):
    pass


class AssemblyAPIClient:
    GENERAL_ENDPOINT = "nzmimeepazxkubdpn"
    COMMITTEE_ENDPOINT = "TVBPMBILL11"
    PLENARY_ENDPOINT = "nwbpacrgavhjryiph"
    SUMMARY_ENDPOINT = "BPMBILLSUMMARY"

    def __init__(self, api_key=None, timeout=15):
        self.api_key = api_key or settings.ASSEMBLY_API_KEY
        self.timeout = timeout
        self.base_url = settings.ASSEMBLY_API_BASE_URL.rstrip("/")

    def _get_rows(self, endpoint, **params):
        query = {
            "KEY": self.api_key,
            "Type": "json",
            "pIndex": 1,
            "pSize": 10,
            **params,
        }
        try:
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                params=query,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise AssemblyAPIError(f"{endpoint} request failed: {exc}") from exc

        blocks = payload.get(endpoint, [])
        if len(blocks) <= 1:
            return []
        return blocks[1].get("row", [])

    def fetch_general_page(self, page, page_size=10):
        return self._get_rows(
            self.GENERAL_ENDPOINT,
            pIndex=page,
            pSize=page_size,
            AGE=22,
        )

    def fetch_committee_rows(self, page_size=100):
        return self._get_rows(self.COMMITTEE_ENDPOINT, pSize=page_size, AGE=22)

    def fetch_plenary_rows(self, page_size=100):
        return self._get_rows(self.PLENARY_ENDPOINT, pSize=page_size, AGE=22)

    def fetch_bill_content(self, bill_no):
        rows = self._get_rows(
            self.SUMMARY_ENDPOINT,
            pSize=1,
            BILL_NO=bill_no,
        )
        if not rows:
            return ""
        return (rows[0].get("SUMMARY") or "").strip()


@dataclass
class SyncCounters:
    fetched: int = 0
    created: int = 0
    updated: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


class BillSyncService:
    ACTIVE_RUN_TIMEOUT = datetime.timedelta(hours=2)

    def __init__(self, client=None):
        self.client = client or AssemblyAPIClient()
        self.categories = None

    def run(
        self,
        pages=1,
        trigger="manual",
        target_count=None,
        known_page_limit=2,
    ):
        sync_run = self._start_run(trigger)
        if sync_run.status == "skipped":
            return sync_run

        counters = SyncCounters()
        try:
            self.categories = ensure_categories()
            self._sync_general_pages(
                pages,
                counters,
                target_count=target_count,
                known_page_limit=known_page_limit,
            )
            self._sync_committee(counters)
            self._sync_plenary(counters)
        except Exception as exc:
            counters.failed += 1
            counters.errors.append(str(exc))
            self._finish_run(sync_run, counters, force_status="failed")
            raise

        status = self._status_for(counters)
        self._finish_run(sync_run, counters, force_status=status)
        return sync_run

    def _start_run(self, trigger):
        now = timezone.now()
        stale_before = now - self.ACTIVE_RUN_TIMEOUT
        try:
            with transaction.atomic():
                stale_runs = SyncRun.objects.filter(status="running", started_at__lt=stale_before)
                stale_runs.update(
                    status="failed",
                    finished_at=now,
                    error_message="실행 중단으로 인한 만료 처리",
                )
                active = SyncRun.objects.filter(
                    status="running", started_at__gte=stale_before
                ).first()
                if active:
                    return SyncRun.objects.create(
                        trigger=trigger,
                        status="skipped",
                        finished_at=now,
                        error_message=f"이미 실행 중인 동기화가 있습니다. run_id={active.pk}",
                    )
                return SyncRun.objects.create(trigger=trigger, status="running")
        except IntegrityError:
            active = SyncRun.objects.filter(status="running").first()
            return SyncRun.objects.create(
                trigger=trigger,
                status="skipped",
                finished_at=now,
                error_message=f"동시에 시작된 동기화를 생략합니다. run_id={active.pk if active else 'unknown'}",
            )

    def _finish_run(self, sync_run, counters, force_status):
        sync_run.status = force_status
        sync_run.finished_at = timezone.now()
        sync_run.fetched_count = counters.fetched
        sync_run.created_count = counters.created
        sync_run.updated_count = counters.updated
        sync_run.failed_count = counters.failed
        sync_run.error_message = "\n".join(counters.errors)[:8000]
        sync_run.save(
            update_fields=[
                "status",
                "finished_at",
                "fetched_count",
                "created_count",
                "updated_count",
                "failed_count",
                "error_message",
            ]
        )

    @staticmethod
    def _status_for(counters):
        if counters.failed:
            return "partial" if counters.fetched else "failed"
        if counters.created == 0 and counters.updated == 0:
            return "no_changes"
        return "success"

    def _sync_general_pages(
        self,
        pages,
        counters,
        target_count=None,
        known_page_limit=2,
    ):
        seen_bill_nos = set()
        known_pages = 0

        for page in range(1, pages + 1):
            try:
                rows = self.client.fetch_general_page(page)
            except AssemblyAPIError as exc:
                counters.failed += 1
                counters.errors.append(str(exc))
                break
            if not rows:
                break

            page_created = 0
            page_updated = 0
            for raw in rows:
                bill_no = raw.get("BILL_NO")
                if bill_no:
                    seen_bill_nos.add(bill_no)

                created, updated = self._handle_row(
                    raw,
                    counters,
                    self._upsert_general_bill,
                )
                counters.fetched += 1
                page_created += int(created)
                page_updated += int(updated)

                if target_count and len(seen_bill_nos) >= target_count:
                    break

            if target_count and len(seen_bill_nos) >= target_count:
                break

            if target_count is None:
                if page_created == 0 and page_updated == 0:
                    known_pages += 1
                else:
                    known_pages = 0
                if known_pages >= known_page_limit:
                    break

    def _sync_committee(self, counters):
        try:
            rows = self.client.fetch_committee_rows()
        except AssemblyAPIError as exc:
            counters.failed += 1
            counters.errors.append(str(exc))
            return
        counters.fetched += len(rows)
        for raw in rows:
            if raw.get("LAW_PROC_DT") or raw.get("LAW_PROC_RESULT_CD"):
                self._handle_row(raw, counters, lambda item: self._upsert_stage_bill(item, "plenary"))

    def _sync_plenary(self, counters):
        try:
            rows = self.client.fetch_plenary_rows()
        except AssemblyAPIError as exc:
            counters.failed += 1
            counters.errors.append(str(exc))
            return
        counters.fetched += len(rows)
        for raw in rows:
            result = raw.get("PROC_RESULT_CD") or ""
            if "가결" in result:
                self._handle_row(raw, counters, lambda item: self._upsert_stage_bill(item, "passed"))

    @staticmethod
    def _handle_row(raw, counters, handler):
        try:
            created, updated = handler(raw)
        except Exception as exc:
            counters.failed += 1
            counters.errors.append(f"bill row failed: {exc}")
            return False, False
        counters.created += int(created)
        counters.updated += int(updated)
        return created, updated

    def _upsert_general_bill(self, raw):
        bill_no = raw.get("BILL_NO")
        if not bill_no:
            raise ValueError("BILL_NO is missing")

        data = {
            "bill_no": bill_no,
            "title": raw.get("BILL_NAME") or "제목 없음",
            "proposer": raw.get("PROPOSER") or "발의자 정보 없음",
            "committee": raw.get("COMMITTEE") or raw.get("COMMITTEE_NAME") or "미정",
            "stage": normalize_stage(raw.get("PROC_RESULT") or "발의"),
            "proposed_at": parse_date(raw.get("PROPOSE_DT")),
            "detail_link": raw.get("DETAIL_LINK") or "",
            "age": 22,
        }
        bill = Bill.objects.filter(bill_id=bill_no).first() or Bill.objects.filter(
            bill_no=bill_no
        ).first()
        return self._save_bill(bill, bill_no, data)

    def _upsert_stage_bill(self, raw, target_stage):
        bill_no = raw.get("BILL_NO")
        if not bill_no:
            raise ValueError("BILL_NO is missing")
        bill = Bill.objects.filter(bill_no=bill_no).first()
        if bill:
            if STAGE_ORDER[target_stage] <= STAGE_ORDER.get(bill.stage, 1):
                return False, False
            bill.stage = target_stage
            bill.synced_at = timezone.now()
            bill.save(update_fields=["stage", "synced_at", "updated_at"])
            return False, True

        raw_title = raw.get("BILL_NAME") or raw.get("BILL_NM") or "제목 없음"
        data = {
            "bill_no": bill_no,
            "title": raw_title.split("(")[0].strip(),
            "proposer": raw.get("PROPOSER") or "발의자 정보 없음",
            "committee": raw.get("CURR_COMMITTEE") or raw.get("COMMITTEE_NM") or "미정",
            "stage": target_stage,
            "proposed_at": parse_date(raw.get("PROPOSE_DT")),
            "detail_link": raw.get("LINK_URL") or "",
            "age": 22,
        }
        return self._save_bill(None, raw.get("BILL_ID") or bill_no, data)

    def _save_bill(self, bill, bill_id, data):
        if bill is None:
            with transaction.atomic():
                bill = Bill.objects.create(
                    bill_id=bill_id,
                    synced_at=timezone.now(),
                    **data,
                )
                map_fallback_categories(bill, bill.committee, self.categories)
                from bills.services.processing import enqueue_processing_tasks

                enqueue_processing_tasks(bill)
            return True, False

        if STAGE_ORDER.get(data["stage"], 1) < STAGE_ORDER.get(bill.stage, 1):
            data["stage"] = bill.stage
        changed = any(getattr(bill, key) != value for key, value in data.items())
        for key, value in data.items():
            setattr(bill, key, value)
        bill.synced_at = timezone.now()
        bill.save()
        return False, changed


def ensure_categories():
    result = {}
    for slug, label, sort_order in CATEGORY_SEED:
        category, _ = Category.objects.update_or_create(
            slug=slug,
            defaults={"label": label, "sort_order": sort_order},
        )
        result[slug] = category
    return result


def normalize_stage(value):
    text = (value or "").strip()
    if any(token in text for token in ("통과", "공포", "가결")):
        return "passed"
    if "본회의" in text:
        return "plenary"
    if "위원회" in text or "심사" in text:
        return "committee"
    return "proposed"


def parse_date(value):
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        return timezone.localdate()


def map_fallback_categories(bill, committee, categories):
    rules = [
        (("환경", "노동"), ("labor", "env")),
        (("보건", "복지", "여성", "가족"), ("welfare", "health")),
        (("국토", "교통"), ("housing",)),
        (("재정", "경제", "정무", "산업", "통상", "벤처"), ("economy",)),
        (("교육", "문화", "체육", "관광"), ("education",)),
        (("과학", "기술", "정보", "방송", "통신"), ("digital",)),
        (("행정", "안전", "국방", "외교", "통일"), ("safety",)),
    ]
    slugs = []
    for keywords, mapped in rules:
        if any(keyword in committee for keyword in keywords):
            slugs.extend(mapped)
    slugs = list(dict.fromkeys(slugs or ["safety"]))
    BillCategory.objects.filter(bill=bill).delete()
    BillCategory.objects.bulk_create(
        [
            BillCategory(bill=bill, category=categories[slug], is_primary=index == 0)
            for index, slug in enumerate(slugs)
        ]
    )


def morning_created_count(day=None):
    day = day or timezone.localdate()
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.datetime.combine(day, datetime.time(9, 0)), tz)
    end = timezone.make_aware(datetime.datetime.combine(day, datetime.time(10, 1)), tz)
    return (
        SyncRun.objects.filter(started_at__gte=start, started_at__lt=end)
        .exclude(status__in=["failed", "skipped"])
        .aggregate(total=Sum("created_count"))["total"]
        or 0
    )


def create_skipped_catchup(reason):
    now = timezone.now()
    return SyncRun.objects.create(
        trigger="catchup",
        status="skipped",
        finished_at=now,
        error_message=reason,
    )
