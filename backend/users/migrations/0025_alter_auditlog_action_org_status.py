from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0024_alter_auditlog_action_update_org_opportunity"),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditlog",
            name="action",
            field=models.CharField(
                choices=[
                    ("SUSPEND", "Suspend user"),
                    ("REACTIVATE", "Reactivate user"),
                    ("TOGGLE_ADMIN", "Toggle admin privilege"),
                    ("TOGGLE_ACTIVE", "Toggle active status"),
                    ("APPROVE_ORG_OPPORTUNITY", "Approve organization opportunity"),
                    ("REJECT_ORG_OPPORTUNITY", "Reject organization opportunity"),
                    ("UPDATE_ORG_OPPORTUNITY", "Update organization opportunity"),
                    ("SUSPEND_ORG_OPPORTUNITY", "Suspend organization opportunity"),
                    ("ACTIVATE_ORG_OPPORTUNITY", "Activate organization opportunity"),
                    ("CLOSE_ORG_OPPORTUNITY", "Close organization opportunity"),
                ],
                db_index=True,
                help_text="Type of admin action performed.",
                max_length=30,
            ),
        ),
    ]
