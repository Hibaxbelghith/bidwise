from django.db import models
from django.db.models import Q
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from pgvector.django import VectorField
from users.models import Utilisateur

class TypeOpportunite(models.TextChoices):
    EMPLOI = "EMPLOI", "Emploi"
    STAGE = "STAGE", "Stage"
    SAISONNIER = "SAISONNIER", "Saisonnier"
    PROJET = "PROJET", "Projet"
    FINANCEMENT = "FINANCEMENT", "Financement"
    RECHERCHE = "RECHERCHE", "Recherche"

class StatutOpportunite(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    EXPIREE = "EXPIREE", "Expirée"
    ARCHIVEE = "ARCHIVEE", "Archivée"

class DateConfidence(models.TextChoices):
    EXACT = "EXACT", "Exacte"
    ESTIMATED = "ESTIMATED", "Estimée"
    FALLBACK = "FALLBACK", "Fallback"


class PipelineRunStatus(models.TextChoices):
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class SourceOpportunite(models.Model):
    nom = models.CharField(max_length=150)
    url = models.URLField()
    type_source = models.CharField(
        max_length=50,
        choices=[
            ("SITE_EMPLOI", "Site d'emploi"),
            ("SITE_STAGE", "Site de stage"),
            ("PORTAIL_PROJET", "Portail de projets"),
            ("AUTRE", "Autre"),
        ]
    )

    def __str__(self):
        return self.nom


class RawOpportuniteProcessingStatus(models.TextChoices):
    NEW = "NEW", "New"
    VALIDATED = "VALIDATED", "Validated"
    REJECTED = "REJECTED", "Rejected"
    MATERIALIZED = "MATERIALIZED", "Materialized"


class RawOpportunite(models.Model):
    source = models.ForeignKey(
        SourceOpportunite,
        on_delete=models.CASCADE,
        related_name="raw_opportunites",
    )
    canonical = models.ForeignKey(
        "Opportunite",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="raw_records",
    )

    # Full source payload is kept so parsing rules can be replayed later without re-scraping.
    raw_payload = models.JSONField()
    raw_titre = models.TextField(blank=True, default="")
    raw_description = models.TextField(blank=True, default="")
    raw_organisation_nom = models.TextField(blank=True, default="")
    raw_type = models.CharField(max_length=100, blank=True, default="")
    raw_status = models.CharField(max_length=100, blank=True, default="")
    raw_date_publication = models.CharField(max_length=100, blank=True, default="")
    raw_date_limite = models.CharField(max_length=100, blank=True, default="")

    source_item_url = models.URLField(max_length=1000, null=True, blank=True)
    source_listing_url = models.URLField(max_length=1000, null=True, blank=True)
    source_record_id = models.CharField(max_length=255, null=True, blank=True)

    # payload_hash tracks exact raw duplicates; content_fingerprint groups near-identical content.
    payload_hash = models.CharField(max_length=40)
    content_fingerprint = models.CharField(max_length=40, blank=True, default="")

    # processing_status lets later stages move records through validation/materialization safely.
    processing_status = models.CharField(
        max_length=20,
        choices=RawOpportuniteProcessingStatus.choices,
        default=RawOpportuniteProcessingStatus.NEW,
    )
    validation_errors = models.JSONField(default=list, blank=True)
    seen_count = models.PositiveIntegerField(default=1)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["payload_hash"], name="raw_opp_payload_hash_idx"),
            models.Index(fields=["content_fingerprint"], name="raw_opp_content_fp_idx"),
            models.Index(fields=["processing_status"], name="raw_opp_status_idx"),
        ]
        constraints = [
            # Source-native identifiers are the strongest dedup key when a scraper exposes them.
            models.UniqueConstraint(
                fields=["source", "source_record_id"],
                condition=Q(source_record_id__isnull=False) & ~Q(source_record_id=""),
                name="uniq_raw_opp_source_record_id",
            ),
            # Direct item URLs are the next best stable key for sources without native IDs.
            models.UniqueConstraint(
                fields=["source", "source_item_url"],
                condition=Q(source_item_url__isnull=False) & ~Q(source_item_url=""),
                name="uniq_raw_opp_source_item_url",
            ),
        ]
        ordering = ["-last_seen_at", "-id"]

    def __str__(self):
        return self.raw_titre or f"Raw opportunity #{self.pk}"


class SimilarityMetrics(models.Model):
    """
    PRINCIPAL-LEVEL: Data-driven metrics for threshold calculation.
    
    Tracks score distribution by opportunity type + embedding model.
    Replaces hardcoded thresholds with data-backed heuristics.
    Updated periodically (daily) from actual similarity searches.
    """
    opportunity_type = models.CharField(max_length=30, choices=TypeOpportunite.choices, unique=True)
    embedding_model = models.CharField(max_length=200, default="default")
    
    # Score distribution (0-1 range)
    score_min = models.FloatField(default=0.0)
    score_max = models.FloatField(default=1.0)
    score_mean = models.FloatField(default=0.5)
    score_p10 = models.FloatField(default=0.3)  # 10th percentile
    score_p25 = models.FloatField(default=0.4)  # 25th percentile
    score_p50 = models.FloatField(default=0.5)  # Median
    score_p75 = models.FloatField(default=0.6)  # 75th percentile
    score_p90 = models.FloatField(default=0.7)  # 90th percentile
    
    # Sample size for confidence
    sample_count = models.IntegerField(default=0)
    
    # Derived thresholds (auto-calculated for convenience)
    recommended_threshold = models.FloatField(default=0.5)  # P50 or P60
    minimum_floor = models.FloatField(default=0.35)         # P10 or lower
    
    # Calibration
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('opportunity_type', 'embedding_model')
    
    def __str__(self):
        return f"{self.opportunity_type} ({self.embedding_model[:20]})"
    
    @property
    def is_confident(self):
        """Metrics are confident if based on sufficient samples."""
        return self.sample_count >= 100
    
    @classmethod
    def get_for_type(cls, opportunity_type, embedding_model="default"):
        """Get metrics for type, or create default if missing."""
        metrics, created = cls.objects.get_or_create(
            opportunity_type=opportunity_type,
            embedding_model=embedding_model,
            defaults={
                'score_p50': 0.5,
                'recommended_threshold': 0.5,
                'minimum_floor': 0.35,
            }
        )
        return metrics


class PipelineRun(models.Model):
    started_at = models.DateTimeField(db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=PipelineRunStatus.choices,
        default=PipelineRunStatus.RUNNING,
        db_index=True,
    )
    processed_count = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    total_processed = models.PositiveIntegerField(default=0)
    total_created = models.PositiveIntegerField(default=0)
    total_updated = models.PositiveIntegerField(default=0)
    total_failed_pages = models.PositiveIntegerField(default=0)
    source = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    error_message = models.TextField(null=True, blank=True)
    duration_seconds = models.FloatField(default=0.0)
    is_stale = models.BooleanField(default=False)

    class Meta:
        ordering = ["-started_at", "-id"]

    @property
    def success_rate(self):
        if not self.total_processed:
            return 0.0
        return (self.total_created + self.total_updated) / self.total_processed

    def __str__(self):
        source = self.source or "unknown"
        return f"PipelineRun<{source}:{self.status}>"


class SourceSchedulerState(models.Model):
    source = models.CharField(max_length=64, unique=True, db_index=True)
    last_dispatched_at = models.DateTimeField(null=True, blank=True)
    last_decision_at = models.DateTimeField(null=True, blank=True)
    last_reason = models.CharField(max_length=80, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source"]

    def __str__(self):
        return f"SourceSchedulerState<{self.source}>"


class ProfileSuggestionType(models.TextChoices):
    SKILL = "SKILL", "Skill"
    ROLE = "ROLE", "Role"
    INTEREST = "INTEREST", "Interest"


class ProfileSuggestion(models.Model):
    term_type = models.CharField(
        max_length=16,
        choices=ProfileSuggestionType.choices,
        db_index=True,
    )
    canonical = models.CharField(max_length=160)
    normalized_key = models.CharField(max_length=180)
    aliases = models.JSONField(blank=True, default=list)
    frequency = models.PositiveIntegerField(default=0, db_index=True)
    confidence = models.FloatField(default=0.0, db_index=True)
    language_counts = models.JSONField(blank=True, default=dict)
    metadata = models.JSONField(blank=True, default=dict)
    is_active = models.BooleanField(default=True, db_index=True)
    last_built_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["term_type", "normalized_key"],
                name="uniq_profile_suggestion_type_key",
            ),
        ]
        indexes = [
            models.Index(
                fields=["term_type", "is_active", "-frequency"],
                name="prof_sugg_type_act_freq_idx",
            ),
            models.Index(
                fields=["term_type", "normalized_key"],
                name="profile_sugg_type_key_idx",
            ),
            models.Index(
                fields=["term_type", "is_active", "normalized_key"],
                name="prof_sugg_type_act_key_idx",
            ),
            models.Index(
                fields=["term_type", "is_active", "confidence", "frequency"],
                name="prof_sugg_quality_idx",
            ),
        ]
        ordering = ["term_type", "-frequency", "canonical"]

    def __str__(self):
        return f"{self.term_type}:{self.canonical}"


class Opportunite(models.Model):
    titre = models.CharField(max_length=255)
    description = models.TextField()
    description_html = models.TextField(blank=True, default="")
    organisation_nom = models.CharField(max_length=255, blank=True, default="")
    company_logo = models.URLField(max_length=1000, blank=True, default="")
    ville = models.CharField(max_length=120, blank=True, default="", db_index=True)
    contract_type = models.CharField(max_length=64, blank=True, default="")
    normalized_contract_types = models.JSONField(
        blank=True,
        default=list,
        help_text="Canonical contract/employment types derived from raw source values",
    )
    experience_min = models.PositiveSmallIntegerField(null=True, blank=True)
    experience_max = models.PositiveSmallIntegerField(null=True, blank=True)
    education_level = models.CharField(max_length=120, blank=True, default="")
    availability = models.CharField(max_length=120, blank=True, default="")
    normalized_work_mode = models.CharField(
        max_length=20,
        blank=True,
        default="UNSPECIFIED",
        help_text="Canonical work mode derived from raw availability/remote values",
    )
    normalized_schedule = models.CharField(
        max_length=20,
        blank=True,
        default="UNSPECIFIED",
        help_text="Canonical schedule derived from raw availability/contract values",
    )
    salary = models.CharField(max_length=120, blank=True, default="")
    experience_years = models.PositiveSmallIntegerField(null=True, blank=True)
    skills = ArrayField(models.CharField(max_length=64), blank=True, default=list)
    normalized_industries = models.JSONField(
        blank=True,
        default=list,
        help_text="Canonical industry/interest sectors derived from source company sector metadata",
    )
    languages = ArrayField(models.CharField(max_length=64), blank=True, default=list)
    languages_fallback = ArrayField(models.CharField(max_length=64), blank=True, default=list)
    extra_data = models.JSONField(blank=True, default=dict)
    date_confidence = models.CharField(
        max_length=16,
        choices=DateConfidence.choices,
        default=DateConfidence.FALLBACK,
        db_index=True,
    )
    quality_score = models.FloatField(default=0.0, db_index=True)
    embedding_vector = models.JSONField(null=True, blank=True)
    embedding_vector_pg = VectorField(dimensions=384, null=True, blank=True)
    embedding_model = models.CharField(max_length=200, blank=True, default="", db_index=True)

    type_opportunite = models.CharField(
        max_length=30,
        choices=TypeOpportunite.choices
    )

    statut = models.CharField(
        max_length=20,
        choices=StatutOpportunite.choices,
        default=StatutOpportunite.ACTIVE
    )

    date_publication = models.DateField()
    date_limite = models.DateField(null=True, blank=True)
    source_item_url = models.URLField(max_length=1000, null=True, blank=True)
    external_id = models.CharField(max_length=64, blank=True, default="", db_index=True)

    organisation = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunites_publiees"
    )

    source = models.ForeignKey(
        SourceOpportunite,
        on_delete=models.CASCADE,
        related_name="opportunites"
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_item_url"],
                condition=Q(source_item_url__isnull=False) & ~Q(source_item_url=""),
                name="uniq_opp_source_item_url",
            ),
        ]
        indexes = [
            models.Index(fields=["type_opportunite", "statut"], name="opp_type_statut_idx"),
            models.Index(fields=["statut"], name="opp_statut_idx"),
            models.Index(fields=["date_publication"], name="opp_date_pub_idx"),
            models.Index(fields=["date_limite"], name="opp_date_limite_idx"),
            models.Index(fields=["date_creation"], name="opp_date_creation_idx"),
            models.Index(fields=["statut", "date_publication"], name="opp_statut_date_pub_idx"),
            GinIndex(fields=["normalized_industries"], name="opp_norm_industries_gin"),
        ]
        ordering = ["-date_publication"]

    def __str__(self):
        return self.titre
