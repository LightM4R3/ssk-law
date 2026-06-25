from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bills.services.assembly import (
    BillSyncService,
    create_skipped_catchup,
    morning_created_count,
)


class Command(BaseCommand):
    help = "국회 OpenAPI 법안을 로컬 DB에 동기화하고 실행 이력을 기록합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pages",
            type=int,
            default=getattr(settings, "ASSEMBLY_SYNC_PAGES", 10),
            help="조회할 일반 법안 API 페이지 수",
        )
        parser.add_argument(
            "--trigger",
            choices=["manual", "scheduled", "catchup"],
            default="manual",
            help="SyncRun에 기록할 실행 유형",
        )
        parser.add_argument(
            "--catch-up-only",
            action="store_true",
            help="오전 신규 법안이 0건인 날에만 실행",
        )
        parser.add_argument(
            "--target-count",
            type=int,
            default=None,
            help="초기 적재 시 확보할 고유 법안 수",
        )
        parser.add_argument(
            "--known-page-limit",
            type=int,
            default=2,
            help="증분 동기화 시 변경 없는 페이지가 연속으로 나오면 중단할 횟수",
        )

    def handle(self, *args, **options):
        if options["pages"] < 1:
            raise CommandError("--pages must be at least 1")
        if options["target_count"] is not None and options["target_count"] < 1:
            raise CommandError("--target-count must be at least 1")
        if options["known_page_limit"] < 1:
            raise CommandError("--known-page-limit must be at least 1")

        if options["catch_up_only"] and morning_created_count() > 0:
            run = create_skipped_catchup("오전 동기화에서 신규 법안을 수집해 13시 보정을 생략합니다.")
            self.stdout.write(self.style.WARNING(f"Skipped catch-up sync. run_id={run.pk}"))
            return

        run = BillSyncService().run(
            pages=options["pages"],
            trigger=options["trigger"],
            target_count=options["target_count"],
            known_page_limit=options["known_page_limit"],
        )
        self.stdout.write(
            f"run_id={run.pk} status={run.status} fetched={run.fetched_count} "
            f"created={run.created_count} updated={run.updated_count} failed={run.failed_count}"
        )
        if run.status == "failed":
            raise CommandError(run.error_message or "Bill synchronization failed")
