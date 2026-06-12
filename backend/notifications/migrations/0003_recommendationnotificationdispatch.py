from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_initial"),
        ("opportunities", "0041_alter_opportunite_statut_suspended_closed"),
        ("users", "0026_organizationprofile_logo"),
    ]

    operations = [
        migrations.CreateModel(
            name="RecommendationNotificationDispatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sent_at", models.DateTimeField(auto_now_add=True)),
                (
                    "notification",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="recommendation_dispatches",
                        to="notifications.notification",
                    ),
                ),
                (
                    "opportunite",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recommendation_notification_dispatches",
                        to="opportunities.opportunite",
                    ),
                ),
                (
                    "utilisateur",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recommendation_notification_dispatches",
                        to="users.utilisateur",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["utilisateur", "sent_at"], name="reco_dispatch_user_sent_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("utilisateur", "opportunite"),
                        name="uniq_recommendation_dispatch_user_opportunity",
                    )
                ],
            },
        ),
    ]
