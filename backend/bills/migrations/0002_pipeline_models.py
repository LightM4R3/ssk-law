from django.db import migrations, models
import django.db.models.deletion


def enqueue_missing_summaries(apps, schema_editor):
    Bill = apps.get_model("bills", "Bill")
    BillProcessingTask = apps.get_model("bills", "BillProcessingTask")
    summarized_ids = set(
        apps.get_model("bills", "BillSummary").objects.values_list("bill_id", flat=True)
    )
    tasks = [
        BillProcessingTask(
            bill_id=bill_id,
            processor="summary",
            processor_version="v1",
            status="pending",
            max_attempts=4,
        )
        for bill_id in Bill.objects.values_list("id", flat=True)
        if bill_id not in summarized_ids
    ]
    BillProcessingTask.objects.bulk_create(tasks, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        ("bills", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SyncRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("trigger", models.CharField(choices=[("manual", "수동"), ("scheduled", "정기"), ("catchup", "13시 보정")], default="manual", max_length=20)),
                ("status", models.CharField(choices=[("running", "실행 중"), ("success", "성공"), ("no_changes", "변경 없음"), ("partial", "부분 성공"), ("failed", "실패"), ("skipped", "건너뜀")], default="running", max_length=20)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("fetched_count", models.PositiveIntegerField(default=0)),
                ("created_count", models.PositiveIntegerField(default=0)),
                ("updated_count", models.PositiveIntegerField(default=0)),
                ("failed_count", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True, default="")),
            ],
            options={"db_table": "sync_run", "ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="BillProcessingTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("processor", models.CharField(max_length=50)),
                ("processor_version", models.CharField(default="v1", max_length=20)),
                ("status", models.CharField(choices=[("pending", "대기"), ("running", "실행 중"), ("retry", "재시도 대기"), ("succeeded", "성공"), ("failed", "실패")], default="pending", max_length=20)),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("max_attempts", models.PositiveIntegerField(default=4)),
                ("next_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True, default="")),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("bill", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="processing_tasks", to="bills.bill")),
            ],
            options={"db_table": "bill_processing_task", "ordering": ["created_at"]},
        ),
        migrations.AddIndex(
            model_name="syncrun",
            index=models.Index(fields=["status", "-started_at"], name="idx_sync_status_time"),
        ),
        migrations.AddConstraint(
            model_name="billprocessingtask",
            constraint=models.UniqueConstraint(fields=("bill", "processor", "processor_version"), name="uq_bill_processor_version"),
        ),
        migrations.AddIndex(
            model_name="billprocessingtask",
            index=models.Index(fields=["status", "next_attempt_at"], name="idx_task_status_due"),
        ),
        migrations.RunPython(enqueue_missing_summaries, migrations.RunPython.noop),
    ]
