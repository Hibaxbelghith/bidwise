from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0025_opportunite_normalized_employment_fields"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE opportunities_opportunite
                    ALTER COLUMN normalized_contract_types SET DEFAULT '[]'::jsonb,
                    ALTER COLUMN normalized_work_mode SET DEFAULT 'UNSPECIFIED',
                    ALTER COLUMN normalized_schedule SET DEFAULT 'UNSPECIFIED';
            """,
            reverse_sql="""
                ALTER TABLE opportunities_opportunite
                    ALTER COLUMN normalized_contract_types DROP DEFAULT,
                    ALTER COLUMN normalized_work_mode DROP DEFAULT,
                    ALTER COLUMN normalized_schedule DROP DEFAULT;
            """,
        ),
    ]
