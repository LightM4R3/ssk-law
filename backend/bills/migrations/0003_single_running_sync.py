from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bills", "0002_pipeline_models"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="syncrun",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "running")),
                fields=("status",),
                name="uq_single_running_sync",
            ),
        ),
    ]
