from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0023_remove_legacy_sources"),
    ]

    operations = [
        migrations.CreateModel(
            name="SourceSchedulerState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(db_index=True, max_length=64, unique=True)),
                ("last_dispatched_at", models.DateTimeField(blank=True, null=True)),
                ("last_decision_at", models.DateTimeField(blank=True, null=True)),
                ("last_reason", models.CharField(blank=True, default="", max_length=80)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["source"],
            },
        ),
    ]
