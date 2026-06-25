import time

from django.core.management.base import BaseCommand, CommandError

from bills.services.processing import BillTaskWorker, load_processors


class Command(BaseCommand):
    help = "대기 중인 법안 후처리 작업을 제한된 수만큼 직렬 처리합니다."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=1)
        parser.add_argument("--processor", type=str, default=None)
        parser.add_argument(
            "--until-empty",
            action="store_true",
            help="현재 처리 가능한 작업이 없을 때까지 반복 실행",
        )
        parser.add_argument(
            "--sleep-seconds",
            type=float,
            default=3,
            help="--until-empty 사용 시 배치 사이 대기 시간",
        )

    def handle(self, *args, **options):
        if options["limit"] < 1:
            raise CommandError("--limit must be at least 1")
        if options["sleep_seconds"] < 0:
            raise CommandError("--sleep-seconds must be zero or greater")
        processors = load_processors()
        processor_key = options["processor"]
        if processor_key and processor_key not in processors:
            raise CommandError(f"Unknown processor: {processor_key}")
        worker = BillTaskWorker(processors=processors)

        if not options["until_empty"]:
            stats = worker.run(
                limit=options["limit"],
                processor_key=processor_key,
            )
            self.stdout.write(self.style.SUCCESS(f"Bill task worker finished: {stats}"))
            return

        totals = {"processed": 0, "succeeded": 0, "retried": 0, "failed": 0}
        batch_number = 0
        while True:
            stats = worker.run(
                limit=options["limit"],
                processor_key=processor_key,
            )
            if stats["processed"] == 0:
                break

            batch_number += 1
            for key in totals:
                totals[key] += stats[key]
            self.stdout.write(f"Bill task batch {batch_number} finished: {stats}")

            if options["sleep_seconds"]:
                time.sleep(options["sleep_seconds"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Bill task worker drained currently due tasks: {totals}"
            )
        )
