import math

from django.db import migrations


BATCH_SIZE = 500
VECTOR_DIMENSIONS = 384


def _is_valid_vector(value):
	if not isinstance(value, list):
		return False
	if len(value) != VECTOR_DIMENSIONS:
		return False
	try:
		casted = [float(item) for item in value]
	except (TypeError, ValueError):
		return False
	return all(math.isfinite(item) for item in casted)


def forward_backfill_pgvector(apps, schema_editor):
	Opportunite = apps.get_model("opportunities", "Opportunite")
	db_alias = schema_editor.connection.alias

	buffer = []
	queryset = (
		Opportunite.objects.using(db_alias)
		.filter(embedding_vector_pg__isnull=True)
		.exclude(embedding_vector__isnull=True)
		.only("id", "embedding_vector")
		.order_by("id")
	)

	for row in queryset.iterator(chunk_size=BATCH_SIZE):
		if not _is_valid_vector(row.embedding_vector):
			continue

		row.embedding_vector_pg = [float(item) for item in row.embedding_vector]
		buffer.append(row)

		if len(buffer) >= BATCH_SIZE:
			Opportunite.objects.using(db_alias).bulk_update(
				buffer,
				["embedding_vector_pg"],
				batch_size=BATCH_SIZE,
			)
			buffer = []

	if buffer:
		Opportunite.objects.using(db_alias).bulk_update(
			buffer,
			["embedding_vector_pg"],
			batch_size=BATCH_SIZE,
		)


def backward_clear_pgvector(apps, schema_editor):
	Opportunite = apps.get_model("opportunities", "Opportunite")
	db_alias = schema_editor.connection.alias
	Opportunite.objects.using(db_alias).update(embedding_vector_pg=None)


class Migration(migrations.Migration):

	dependencies = [
		("opportunities", "0009_opportunite_embedding_vector_pg"),
	]

	operations = [
		migrations.RunPython(forward_backfill_pgvector, backward_clear_pgvector),
	]
