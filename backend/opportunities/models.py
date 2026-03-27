from django.db import models
from django.contrib.postgres.fields import ArrayField
from users.models import Utilisateur
from datetime import datetime, timedelta

class TypeOpportunite(models.TextChoices):
    EMPLOI = "EMPLOI", "Emploi"
    STAGE = "STAGE", "Stage"
    PROJET = "PROJET", "Projet"
    FINANCEMENT = "FINANCEMENT", "Financement"
    RECHERCHE = "RECHERCHE", "Recherche"

class StatutOpportunite(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    EXPIREE = "EXPIREE", "Expirée"
    ARCHIVEE = "ARCHIVEE", "Archivée"


class SourceOpportunite(models.Model):
    nom = models.CharField(max_length=150)
    url = models.URLField()
    type_source = models.CharField(
        max_length=50,
        choices=[
            ("SITE_EMPLOI", "Site d'emploi"),
            ("PORTAIL_PROJET", "Portail de projets"),
            ("AUTRE", "Autre"),
        ]
    )

    def __str__(self):
        return self.nom


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


class Opportunite(models.Model):
    titre = models.CharField(max_length=255)
    description = models.TextField()
    organisation_nom = models.CharField(max_length=255, blank=True, default="")
    embedding_vector = models.JSONField(null=True, blank=True)
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
                fields=["titre", "source", "date_publication"],
                name="uniq_opp_title_source_pub",
            ),
        ]
        indexes = [
            models.Index(fields=["type_opportunite", "statut"], name="opp_type_statut_idx"),
            models.Index(fields=["statut"], name="opp_statut_idx"),
            models.Index(fields=["date_publication"], name="opp_date_pub_idx"),
            models.Index(fields=["date_limite"], name="opp_date_limite_idx"),
            models.Index(fields=["date_creation"], name="opp_date_creation_idx"),
            models.Index(fields=["statut", "date_publication"], name="opp_statut_date_pub_idx"),
        ]
        ordering = ["-date_publication"]

    def __str__(self):
        return self.titre
