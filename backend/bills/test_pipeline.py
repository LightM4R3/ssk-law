import datetime
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from bills.models import (
    Bill,
    BillProcessingTask,
    BillSummary,
    SimilarBill,
    SyncRun,
)
from bills.services.assembly import (
    AssemblyAPIError,
    BillSyncService,
    ensure_categories,
)
from bills.services.processing import BillProcessor, BillTaskWorker
from bills.services.processors import SummaryProcessor
from services.ollama import PLAIN_DISCLAIMER, clean_plain_text


def bill_row(bill_no="TEST-001", title="신규 테스트 법안"):
    return {
        "BILL_NO": bill_no,
        "BILL_NAME": title,
        "PROPOSER": "테스트 의원",
        "COMMITTEE": "환경노동위원회",
        "DETAIL_LINK": "https://example.com/bill",
        "PROPOSE_DT": "2026-06-22",
        "PROC_RESULT": "발의",
    }


def create_bill(bill_no="TEST-001"):
    return Bill.objects.create(
        bill_id=bill_no,
        bill_no=bill_no,
        title="테스트 법안",
        proposer="테스트 의원",
        committee="환경노동위원회",
        proposed_at=datetime.date(2026, 6, 22),
    )


class FakeAssemblyClient:
    def __init__(self, pages=None, committee=None, plenary=None):
        self.pages = pages or {}
        self.committee = committee or []
        self.plenary = plenary or []

    def fetch_general_page(self, page, page_size=10):
        value = self.pages.get(page, [])
        if isinstance(value, Exception):
            raise value
        return value

    def fetch_committee_rows(self, page_size=100):
        if isinstance(self.committee, Exception):
            raise self.committee
        return self.committee

    def fetch_plenary_rows(self, page_size=100):
        if isinstance(self.plenary, Exception):
            raise self.plenary
        return self.plenary


class BillSyncPipelineTests(TestCase):
    def test_new_bill_is_visible_and_summary_task_is_enqueued(self):
        run = BillSyncService(client=FakeAssemblyClient(pages={1: [bill_row()]})).run(
            pages=2,
            trigger="scheduled",
        )

        bill = Bill.objects.get(bill_no="TEST-001")
        self.assertEqual(run.status, "success")
        self.assertEqual(run.created_count, 1)
        self.assertTrue(bill.categories.filter(slug="labor").exists())
        self.assertTrue(
            BillProcessingTask.objects.filter(
                bill=bill,
                processor="summary",
                status="pending",
            ).exists()
        )

        response = APIClient().get(reverse("bills-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["bills"][0]["summaryStatus"], "pending")

    def test_repeated_sync_does_not_duplicate_or_report_an_update(self):
        client = FakeAssemblyClient(pages={1: [bill_row()]})
        BillSyncService(client=client).run(pages=1)
        second = BillSyncService(client=client).run(pages=1)

        self.assertEqual(Bill.objects.filter(bill_no="TEST-001").count(), 1)
        self.assertEqual(second.created_count, 0)
        self.assertEqual(second.updated_count, 0)
        self.assertEqual(second.status, "no_changes")

    def test_partial_api_failure_is_recorded(self):
        client = FakeAssemblyClient(
            pages={
                1: [bill_row()],
                2: AssemblyAPIError("page 2 timeout"),
            }
        )
        run = BillSyncService(client=client).run(pages=2)

        self.assertEqual(run.status, "partial")
        self.assertEqual(run.created_count, 1)
        self.assertEqual(run.failed_count, 1)
        self.assertIn("page 2 timeout", run.error_message)

    def test_target_count_stops_initial_load_at_unique_bill_limit(self):
        client = FakeAssemblyClient(
            pages={
                1: [
                    bill_row("TEST-001"),
                    bill_row("TEST-002"),
                    bill_row("TEST-003"),
                    bill_row("TEST-004"),
                ]
            }
        )

        run = BillSyncService(client=client).run(
            pages=5,
            target_count=3,
        )

        self.assertEqual(run.created_count, 3)
        self.assertEqual(run.fetched_count, 3)
        self.assertEqual(Bill.objects.count(), 3)
        self.assertFalse(Bill.objects.filter(bill_no="TEST-004").exists())

    def test_incremental_sync_stops_after_consecutive_known_pages(self):
        BillSyncService(
            client=FakeAssemblyClient(
                pages={
                    1: [bill_row("TEST-001")],
                    2: [bill_row("TEST-002")],
                }
            )
        ).run(pages=2)
        client = FakeAssemblyClient(
            pages={
                1: [bill_row("TEST-001")],
                2: [bill_row("TEST-002")],
                3: [bill_row("TEST-003")],
            }
        )
        client.fetch_general_page = MagicMock(side_effect=client.fetch_general_page)

        BillSyncService(client=client).run(
            pages=3,
            known_page_limit=2,
        )

        self.assertEqual(client.fetch_general_page.call_count, 2)
        self.assertFalse(Bill.objects.filter(bill_no="TEST-003").exists())

    def test_second_sync_is_skipped_while_another_run_is_active(self):
        active = SyncRun.objects.create(trigger="scheduled", status="running")
        client = MagicMock(spec=FakeAssemblyClient)

        skipped = BillSyncService(client=client).run(pages=1)

        self.assertEqual(skipped.status, "skipped")
        self.assertIn(f"run_id={active.pk}", skipped.error_message)
        client.fetch_general_page.assert_not_called()

    def test_catchup_is_skipped_when_morning_created_a_bill(self):
        morning = SyncRun.objects.create(
            trigger="scheduled",
            status="success",
            finished_at=timezone.now(),
            created_count=1,
        )
        local_now = timezone.localtime()
        morning_time = local_now.replace(hour=9, minute=30, second=0, microsecond=0)
        SyncRun.objects.filter(pk=morning.pk).update(started_at=morning_time)

        with patch("bills.management.commands.sync_bills.BillSyncService.run") as run_sync:
            call_command(
                "sync_bills",
                pages=1,
                trigger="catchup",
                catch_up_only=True,
            )

        run_sync.assert_not_called()
        self.assertTrue(SyncRun.objects.filter(trigger="catchup", status="skipped").exists())

    def test_catchup_runs_when_morning_created_no_bills(self):
        morning = SyncRun.objects.create(
            trigger="scheduled",
            status="no_changes",
            finished_at=timezone.now(),
            created_count=0,
        )
        local_now = timezone.localtime()
        morning_time = local_now.replace(hour=9, minute=30, second=0, microsecond=0)
        SyncRun.objects.filter(pk=morning.pk).update(started_at=morning_time)
        completed = SyncRun.objects.create(
            trigger="catchup",
            status="no_changes",
            finished_at=timezone.now(),
        )

        with patch(
            "bills.management.commands.sync_bills.BillSyncService.run",
            return_value=completed,
        ) as run_sync:
            call_command(
                "sync_bills",
                pages=1,
                trigger="catchup",
                catch_up_only=True,
            )

        run_sync.assert_called_once_with(
            pages=1,
            trigger="catchup",
            target_count=None,
            known_page_limit=2,
        )


@override_settings(BILL_TASK_RETRY_DELAYS=[60, 300, 1800])
class BillProcessingTests(TestCase):
    def setUp(self):
        ensure_categories()
        self.bill = create_bill()

    @patch("bills.management.commands.process_bill_tasks.time.sleep")
    @patch("bills.management.commands.process_bill_tasks.BillTaskWorker")
    @patch("bills.management.commands.process_bill_tasks.load_processors")
    def test_process_command_until_empty_stops_when_no_due_tasks_remain(
        self,
        load_registered_processors,
        worker_class,
        sleep,
    ):
        load_registered_processors.return_value = {"summary": MagicMock()}
        worker_class.return_value.run.side_effect = [
            {"processed": 5, "succeeded": 4, "retried": 1, "failed": 0},
            {"processed": 2, "succeeded": 2, "retried": 0, "failed": 0},
            {"processed": 0, "succeeded": 0, "retried": 0, "failed": 0},
        ]
        output = StringIO()

        call_command(
            "process_bill_tasks",
            limit=5,
            until_empty=True,
            sleep_seconds=0,
            stdout=output,
        )

        self.assertEqual(worker_class.return_value.run.call_count, 3)
        sleep.assert_not_called()
        self.assertIn("'processed': 7", output.getvalue())

    @patch("bills.services.processors.ollama.summarize_bill")
    @patch.object(SummaryProcessor, "__init__", return_value=None)
    def test_summary_success_is_stored(self, mock_init, summarize):
        summarize.return_value = {
            "summary_1": "첫 번째 요약",
            "summary_2": "두 번째 요약",
            "summary_3": "세 번째 요약",
            "impact": "예상 영향",
            "categories": ["labor"],
        }
        processor = SummaryProcessor()
        processor.client = MagicMock()
        processor.client.fetch_bill_content.return_value = "법안 상세 내용"
        task = BillProcessingTask.objects.create(
            bill=self.bill,
            processor="summary",
            max_attempts=4,
        )

        stats = BillTaskWorker(processors={"summary": processor}).run(limit=1)

        task.refresh_from_db()
        self.assertEqual(stats["succeeded"], 1)
        self.assertEqual(task.status, "succeeded")
        self.assertEqual(self.bill.summary.summary_3, "세 번째 요약")
        self.assertTrue(self.bill.categories.filter(slug="labor").exists())

    def test_invalid_summary_retries_three_times_then_fails(self):
        processor = MagicMock(spec=BillProcessor)
        processor.key = "summary"
        processor.dependencies = ()
        processor.process.side_effect = ValueError("invalid AI response")
        task = BillProcessingTask.objects.create(
            bill=self.bill,
            processor="summary",
            max_attempts=4,
        )
        worker = BillTaskWorker(processors={"summary": processor})

        for attempt in range(4):
            worker.run(limit=1)
            task.refresh_from_db()
            if attempt < 3:
                self.assertEqual(task.status, "retry")
                task.next_attempt_at = timezone.now()
                task.save(update_fields=["next_attempt_at"])

        task.refresh_from_db()
        self.assertEqual(task.attempt_count, 4)
        self.assertEqual(task.status, "failed")
        self.assertIn("invalid AI response", task.last_error)

    def test_similarity_failure_does_not_remove_summary_or_bill(self):
        BillSummary.objects.create(
            bill=self.bill,
            summary_1="첫 번째",
            summary_2="두 번째",
            summary_3="세 번째",
        )

        class FailingSimilarityProcessor(BillProcessor):
            key = "similarity"
            dependencies = ("summary",)

            def process(self, bill):
                raise RuntimeError("similarity unavailable")

        task = BillProcessingTask.objects.create(
            bill=self.bill,
            processor="similarity",
            max_attempts=1,
        )
        BillTaskWorker(
            processors={"similarity": FailingSimilarityProcessor()}
        ).run(limit=1)

        task.refresh_from_db()
        self.assertEqual(task.status, "failed")
        self.assertTrue(BillSummary.objects.filter(bill=self.bill).exists())
        self.assertTrue(Bill.objects.filter(pk=self.bill.pk).exists())


class DatabaseOnlyApiTests(TestCase):
    def setUp(self):
        ensure_categories()
        self.bill = create_bill()
        BillProcessingTask.objects.create(bill=self.bill, processor="summary")
        self.client = APIClient()

    @patch("requests.post")
    @patch("requests.get")
    def test_regular_get_endpoints_do_not_call_external_services(self, get, post):
        urls = [
            reverse("categories"),
            reverse("picks"),
            reverse("bills-list"),
            reverse("bill-detail", kwargs={"bill_id": self.bill.bill_id}),
            reverse("sync-status"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        get.assert_not_called()
        post.assert_not_called()

    def test_sync_status_uses_saved_run(self):
        run = SyncRun.objects.create(
            trigger="scheduled",
            status="success",
            finished_at=timezone.now(),
            created_count=2,
        )
        response = self.client.get(reverse("sync-status"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["createdCount"], 2)
        self.assertIsNotNone(response.data["lastSuccessAt"])


class SearchResponseTests(TestCase):
    def setUp(self):
        ensure_categories()
        self.bill = create_bill("SCHOOL-001")
        self.bill.title = "중·고등학교 무상급식 확대법"
        self.bill.save(update_fields=["title"])
        BillSummary.objects.create(
            bill=self.bill,
            summary_1="학교 무상급식 지원 범위를 확대합니다.",
            summary_2="지역별 지원 격차를 줄입니다.",
            summary_3="학생의 급식 접근성을 높입니다.",
        )
        self.client = APIClient()

    @patch("requests.post")
    def test_search_returns_db_results_without_calling_ollama(self, post):
        response = self.client.post(
            reverse("search"),
            {"query": "학교"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["aiPending"])
        self.assertEqual(response.data["bills"][0]["id"], self.bill.bill_id)
        post.assert_not_called()

    @patch("bills.views.explain_search", return_value="학교 급식 지원 범위를 확대하는 법안입니다.")
    def test_search_explanation_is_loaded_separately(self, explain):
        response = self.client.post(
            reverse("search-explain"),
            {"query": "학교"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["aiStatus"], "ready")
        self.assertIn(PLAIN_DISCLAIMER, response.data["intro"])
        explain.assert_called_once()

    def test_model_output_is_normalized_to_short_plain_text(self):
        raw = "## 안내\n**학교 급식**을 설명할게요. 😊\n---\n* 핵심 내용입니다."
        cleaned = clean_plain_text(raw, max_chars=100)

        self.assertNotIn("#", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("😊", cleaned)
        self.assertNotIn("---", cleaned)
        self.assertLessEqual(len(cleaned), 100)
