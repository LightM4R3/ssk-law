import datetime

from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone
from django.utils.module_loading import import_string

from bills.models import BillProcessingTask, BillSummary


class BillProcessor:
    key = ""
    version = "v1"
    dependencies = ()

    def process(self, bill):
        raise NotImplementedError


def load_processors():
    paths = getattr(
        settings,
        "BILL_PROCESSORS",
        ["bills.services.processors.SummaryProcessor"],
    )
    processors = {}
    for path in paths:
        processor = import_string(path)()
        if not processor.key:
            raise ValueError(f"Processor key is missing: {path}")
        if processor.key in processors:
            raise ValueError(f"Duplicate processor key: {processor.key}")
        processors[processor.key] = processor
    return processors


def enqueue_processing_tasks(bill, processor_key=None):
    created_tasks = []
    for processor in load_processors().values():
        if processor_key and processor.key != processor_key:
            continue
        initial_status = "succeeded" if processor.key == "summary" and hasattr(bill, "summary") else "pending"
        task, created = BillProcessingTask.objects.get_or_create(
            bill=bill,
            processor=processor.key,
            processor_version=processor.version,
            defaults={
                "status": initial_status,
                "max_attempts": len(getattr(settings, "BILL_TASK_RETRY_DELAYS", [60, 300, 1800])) + 1,
                "finished_at": timezone.now() if initial_status == "succeeded" else None,
            },
        )
        if created:
            created_tasks.append(task)
    return created_tasks


class BillTaskWorker:
    def __init__(self, processors=None):
        self.processors = processors or load_processors()
        self.retry_delays = getattr(settings, "BILL_TASK_RETRY_DELAYS", [60, 300, 1800])

    def run(self, limit=10, processor_key=None):
        self._recover_stale_tasks()
        now = timezone.now()
        due = BillProcessingTask.objects.filter(
            status__in=["pending", "retry"]
        ).filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now))
        if processor_key:
            due = due.filter(processor=processor_key)

        stats = {"processed": 0, "succeeded": 0, "retried": 0, "failed": 0}
        for task_id in due.order_by("created_at").values_list("id", flat=True).iterator():
            if stats["processed"] >= limit:
                break
            task = BillProcessingTask.objects.select_related("bill").get(pk=task_id)
            processor = self.processors.get(task.processor)
            if processor is None:
                self._mark_permanent_failure(task, f"Processor is not registered: {task.processor}")
                stats["processed"] += 1
                stats["failed"] += 1
                continue
            if not self._dependencies_ready(task.bill, processor.dependencies):
                continue

            task = self._claim(task.pk)
            if task is None:
                continue
            stats["processed"] += 1
            try:
                processor.process(task.bill)
            except Exception as exc:
                final = self._mark_failure(task, exc)
                stats["failed" if final else "retried"] += 1
            else:
                self._mark_success(task)
                stats["succeeded"] += 1
        return stats

    @staticmethod
    def _claim(task_id):
        now = timezone.now()
        claimed = BillProcessingTask.objects.filter(
            pk=task_id,
            status__in=["pending", "retry"],
        ).update(
            status="running",
            attempt_count=F("attempt_count") + 1,
            started_at=now,
            next_attempt_at=None,
            updated_at=now,
        )
        if not claimed:
            return None
        return BillProcessingTask.objects.select_related("bill").get(pk=task_id)

    @staticmethod
    def _dependencies_ready(bill, dependencies):
        for dependency in dependencies:
            if dependency == "summary" and BillSummary.objects.filter(bill=bill).exists():
                continue
            if not BillProcessingTask.objects.filter(
                bill=bill,
                processor=dependency,
                status="succeeded",
            ).exists():
                return False
        return True

    @staticmethod
    def _mark_success(task):
        now = timezone.now()
        BillProcessingTask.objects.filter(pk=task.pk).update(
            status="succeeded",
            finished_at=now,
            next_attempt_at=None,
            last_error="",
            updated_at=now,
        )

    def _mark_failure(self, task, exc):
        now = timezone.now()
        error = f"{type(exc).__name__}: {exc}"[:8000]
        if task.attempt_count >= task.max_attempts:
            BillProcessingTask.objects.filter(pk=task.pk).update(
                status="failed",
                finished_at=now,
                next_attempt_at=None,
                last_error=error,
                updated_at=now,
            )
            return True

        delay_index = min(task.attempt_count - 1, len(self.retry_delays) - 1)
        next_attempt = now + datetime.timedelta(seconds=self.retry_delays[delay_index])
        BillProcessingTask.objects.filter(pk=task.pk).update(
            status="retry",
            next_attempt_at=next_attempt,
            last_error=error,
            updated_at=now,
        )
        return False

    @staticmethod
    def _mark_permanent_failure(task, error):
        now = timezone.now()
        BillProcessingTask.objects.filter(pk=task.pk).update(
            status="failed",
            finished_at=now,
            next_attempt_at=None,
            last_error=error[:8000],
            updated_at=now,
        )

    @staticmethod
    def _recover_stale_tasks():
        stale_minutes = getattr(settings, "BILL_TASK_STALE_MINUTES", 10)
        cutoff = timezone.now() - datetime.timedelta(minutes=stale_minutes)
        BillProcessingTask.objects.filter(status="running", started_at__lt=cutoff).update(
            status="retry",
            next_attempt_at=timezone.now(),
            last_error="이전 worker가 완료되지 않아 재시도합니다.",
        )
