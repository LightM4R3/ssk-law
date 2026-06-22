from django.contrib import admin

from .models import BillProcessingTask, SyncRun


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = (
        "started_at",
        "trigger",
        "status",
        "fetched_count",
        "created_count",
        "updated_count",
        "failed_count",
    )
    list_filter = ("trigger", "status")


@admin.register(BillProcessingTask)
class BillProcessingTaskAdmin(admin.ModelAdmin):
    list_display = (
        "bill",
        "processor",
        "processor_version",
        "status",
        "attempt_count",
        "next_attempt_at",
    )
    list_filter = ("processor", "status")
    search_fields = ("bill__bill_id", "bill__title")
