from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0019_remove_opportunite_uniq_opp_title_source_pub_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunite",
            name="extra_data",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
