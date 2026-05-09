from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0027_profilesuggestion"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="profilesuggestion",
            index=models.Index(
                fields=["term_type", "is_active", "normalized_key"],
                name="prof_sugg_type_act_key_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="profilesuggestion",
            index=models.Index(
                fields=["term_type", "is_active", "confidence", "frequency"],
                name="prof_sugg_quality_idx",
            ),
        ),
    ]
