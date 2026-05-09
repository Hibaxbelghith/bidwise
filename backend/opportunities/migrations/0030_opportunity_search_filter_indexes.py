from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("opportunities", "0029_opportunity_industries_and_interest_suggestions"),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS source_nom_idx
            ON opportunities_sourceopportunite (nom);
            """,
            reverse_sql="DROP INDEX CONCURRENTLY IF EXISTS source_nom_idx;",
        ),
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS opp_active_quality_date_idx
            ON opportunities_opportunite (statut, quality_score DESC, date_publication DESC, id DESC);
            """,
            reverse_sql="DROP INDEX CONCURRENTLY IF EXISTS opp_active_quality_date_idx;",
        ),
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS opp_status_type_quality_date_idx
            ON opportunities_opportunite (statut, type_opportunite, quality_score DESC, date_publication DESC, id DESC);
            """,
            reverse_sql="DROP INDEX CONCURRENTLY IF EXISTS opp_status_type_quality_date_idx;",
        ),
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS opp_status_location_quality_date_idx
            ON opportunities_opportunite (statut, ville, quality_score DESC, date_publication DESC, id DESC);
            """,
            reverse_sql="DROP INDEX CONCURRENTLY IF EXISTS opp_status_location_quality_date_idx;",
        ),
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS opp_status_source_quality_date_idx
            ON opportunities_opportunite (statut, source_id, quality_score DESC, date_publication DESC, id DESC);
            """,
            reverse_sql="DROP INDEX CONCURRENTLY IF EXISTS opp_status_source_quality_date_idx;",
        ),
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS opp_status_workmode_quality_date_idx
            ON opportunities_opportunite (statut, normalized_work_mode, quality_score DESC, date_publication DESC, id DESC);
            """,
            reverse_sql="DROP INDEX CONCURRENTLY IF EXISTS opp_status_workmode_quality_date_idx;",
        ),
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS opp_status_created_idx
            ON opportunities_opportunite (statut, date_creation DESC, id DESC);
            """,
            reverse_sql="DROP INDEX CONCURRENTLY IF EXISTS opp_status_created_idx;",
        ),
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS opp_role_experience_idx
            ON opportunities_opportunite (type_opportunite, normalized_work_mode, experience_min, experience_max);
            """,
            reverse_sql="DROP INDEX CONCURRENTLY IF EXISTS opp_role_experience_idx;",
        ),
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS opp_title_trgm_idx
            ON opportunities_opportunite USING gin (titre gin_trgm_ops);
            """,
            reverse_sql="DROP INDEX CONCURRENTLY IF EXISTS opp_title_trgm_idx;",
        ),
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS opp_company_trgm_idx
            ON opportunities_opportunite USING gin (organisation_nom gin_trgm_ops);
            """,
            reverse_sql="DROP INDEX CONCURRENTLY IF EXISTS opp_company_trgm_idx;",
        ),
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS opp_location_trgm_idx
            ON opportunities_opportunite USING gin (ville gin_trgm_ops);
            """,
            reverse_sql="DROP INDEX CONCURRENTLY IF EXISTS opp_location_trgm_idx;",
        ),
        migrations.RunSQL(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS opp_description_trgm_idx
            ON opportunities_opportunite USING gin (description gin_trgm_ops);
            """,
            reverse_sql="DROP INDEX CONCURRENTLY IF EXISTS opp_description_trgm_idx;",
        ),
    ]
