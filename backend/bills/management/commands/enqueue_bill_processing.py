from django.core.management.base import BaseCommand, CommandError

from bills.models import Bill
from bills.services.processing import enqueue_processing_tasks, load_processors


class Command(BaseCommand):
    help = "기존 법안에 등록된 processor 작업을 멱등적으로 생성합니다."

    def add_arguments(self, parser):
        parser.add_argument("--processor", type=str, default=None)

    def handle(self, *args, **options):
        processor_key = options["processor"]
        processors = load_processors()
        if processor_key and processor_key not in processors:
            raise CommandError(f"Unknown processor: {processor_key}")

        created = 0
        for bill in Bill.objects.all().iterator():
            created += len(enqueue_processing_tasks(bill, processor_key=processor_key))
        self.stdout.write(self.style.SUCCESS(f"Created {created} processing task(s)."))

