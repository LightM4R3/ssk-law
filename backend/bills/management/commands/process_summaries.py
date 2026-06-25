from django.core.management.base import BaseCommand

from bills.models import Bill
from bills.services.processing import BillTaskWorker, enqueue_processing_tasks


class Command(BaseCommand):
    help = "호환용 명령: 요약 작업을 등록하고 후처리 worker를 실행합니다."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        for bill in Bill.objects.filter(summary__isnull=True).iterator():
            enqueue_processing_tasks(bill, processor_key="summary")
        stats = BillTaskWorker().run(limit=options["limit"], processor_key="summary")
        self.stdout.write(self.style.SUCCESS(f"Summary worker finished: {stats}"))
