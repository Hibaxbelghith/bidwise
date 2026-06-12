from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0025_alter_auditlog_action_org_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="organizationprofile",
            name="logo",
            field=models.URLField(blank=True, default="", max_length=1000),
        ),
    ]
