from django.db import migrations
import pgvector.django.vector


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0008_rawopportunite_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AddField(
            model_name="opportunite",
            name="embedding_vector_pg",
            field=pgvector.django.vector.VectorField(blank=True, dimensions=384, null=True),
        ),
    ]
