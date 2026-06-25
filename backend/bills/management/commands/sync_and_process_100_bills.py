from django.core.management.base import BaseCommand, CommandError

from bills.services.assembly import BillSyncService
from bills.services.processing import BillTaskWorker


class Command(BaseCommand):
    help = "호환용 명령: 법안을 동기화한 뒤 제한된 수의 요약 작업을 처리합니다."

    def add_arguments(self, parser):
        parser.add_argument("--pages", type=int, default=10)
        parser.add_argument("--limit-llm", type=int, default=100)

    def handle(self, *args, **options):
        run = BillSyncService().run(pages=options["pages"], trigger="manual")
        if run.status == "failed":
            raise CommandError(run.error_message or "Bill synchronization failed")
        stats = BillTaskWorker().run(
            limit=options["limit_llm"],
            processor_key="summary",
        )
        self.stdout.write(
            self.style.SUCCESS(f"Sync run {run.pk} ({run.status}), summary worker: {stats}")
        )
