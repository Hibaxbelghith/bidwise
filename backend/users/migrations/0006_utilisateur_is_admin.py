from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_loginevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="utilisateur",
            name="is_admin",
            field=models.BooleanField(
                default=False,
                help_text="Can access BidWise admin backoffice APIs.",
            ),
        ),
    ]
