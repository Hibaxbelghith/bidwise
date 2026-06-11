from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0004_alter_candidature_url_source_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="candidature",
            name="cover_letter",
        ),
        migrations.AddField(
            model_name="candidature",
            name="contact_email",
            field=models.EmailField(blank=True, default="", max_length=254),
        ),
        migrations.AddField(
            model_name="candidature",
            name="contact_phone",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="candidature",
            name="cover_letter_url",
            field=models.URLField(blank=True, default="", max_length=1000),
        ),
    ]
