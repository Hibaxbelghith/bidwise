from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("opportunities", "0010_backfill_embedding_vector_pg"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS opp_embedding_pg_ivfflat_idx "
                "ON opportunities_opportunite "
                "USING ivfflat (embedding_vector_pg vector_cosine_ops) "
                "WITH (lists = 100) "
                "WHERE embedding_vector_pg IS NOT NULL"
            ),
            reverse_sql=(
                "DROP INDEX CONCURRENTLY IF EXISTS opp_embedding_pg_ivfflat_idx"
            ),
        ),
        migrations.RunSQL(
            sql="ANALYZE opportunities_opportunite",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
