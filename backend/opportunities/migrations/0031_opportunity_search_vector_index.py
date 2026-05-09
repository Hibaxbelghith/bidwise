from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("opportunities", "0030_opportunity_search_filter_indexes"),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS opp_search_vector_gin_idx
            ON opportunities_opportunite USING gin ((
                setweight(to_tsvector('simple', coalesce(titre, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(organisation_nom, '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(ville, '')), 'C') ||
                setweight(to_tsvector('simple', coalesce(description, '')), 'D')
            ));
            """,
            reverse_sql="DROP INDEX CONCURRENTLY IF EXISTS opp_search_vector_gin_idx;",
        ),
    ]
