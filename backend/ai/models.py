from django.db import models
from pgvector.django import VectorField


class ESCOOccupation(models.Model):
    uri = models.CharField(max_length=255, unique=True)

    preferred_label = models.CharField(max_length=255)

    family = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    isco_group = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    alternate_labels = models.JSONField(default=list)

    related_skills = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["preferred_label"]),
            models.Index(fields=["family"]),
            models.Index(fields=["isco_group"]),
        ]

    def __str__(self):
        return self.preferred_label


class ESCOSkill(models.Model):
    uri = models.CharField(max_length=255, unique=True)

    preferred_label = models.CharField(max_length=255)

    alt_labels = models.JSONField(default=list)

    preferred_label_en = models.CharField(max_length=255, blank=True, default="")

    preferred_label_fr = models.CharField(max_length=255, blank=True, default="")

    alt_labels_en = models.JSONField(default=list, blank=True)

    alt_labels_fr = models.JSONField(default=list, blank=True)

    hidden_labels_en = models.JSONField(default=list, blank=True)

    hidden_labels_fr = models.JSONField(default=list, blank=True)

    search_text_multilingual = models.TextField(blank=True, default="")

    embedding = VectorField(dimensions=384, null=True, blank=True)

    embedding_model = models.CharField(max_length=200, blank=True, default="")

    embedding_dimensions = models.PositiveIntegerField(null=True, blank=True)

    embedding_version = models.CharField(max_length=64, blank=True, default="")

    embedding_updated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["preferred_label"]),
            models.Index(fields=["preferred_label_en"]),
            models.Index(fields=["preferred_label_fr"]),
            models.Index(fields=["embedding_model", "embedding_version"]),
            models.Index(fields=["embedding_dimensions"]),
        ]
        ordering = ["preferred_label", "uri"]

    def __str__(self):
        return self.preferred_label


class BidWiseSkillAlias(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        REVIEW = "REVIEW", "Review"
        DISABLED = "DISABLED", "Disabled"

    alias = models.CharField(max_length=255, unique=True)

    normalized_key = models.CharField(max_length=255, db_index=True)

    language = models.CharField(max_length=16, blank=True, default="")

    target_skill = models.ForeignKey(
        ESCOSkill,
        on_delete=models.CASCADE,
        related_name="bidwise_aliases",
    )

    source = models.CharField(max_length=64, blank=True, default="")

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["normalized_key", "status"]),
            models.Index(fields=["target_skill", "status"]),
            models.Index(fields=["language"]),
        ]
        ordering = ["alias", "id"]

    def __str__(self):
        return self.alias


class ESCOOccupationCatalog(models.Model):
    uri = models.CharField(max_length=255, unique=True)

    preferred_label_en = models.CharField(max_length=255, blank=True, default="")

    preferred_label_fr = models.CharField(max_length=255, blank=True, default="")

    alt_labels_en = models.JSONField(default=list, blank=True)

    alt_labels_fr = models.JSONField(default=list, blank=True)

    hidden_labels_en = models.JSONField(default=list, blank=True)

    hidden_labels_fr = models.JSONField(default=list, blank=True)

    search_text_multilingual = models.TextField(blank=True, default="")

    isco_group = models.CharField(max_length=20, blank=True, default="")

    code = models.CharField(max_length=64, blank=True, default="")

    nace_code = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["preferred_label_en"]),
            models.Index(fields=["preferred_label_fr"]),
            models.Index(fields=["isco_group"]),
        ]
        ordering = ["preferred_label_en", "preferred_label_fr", "uri"]

    def __str__(self):
        return self.preferred_label_en or self.preferred_label_fr or self.uri


class ESCOOccupationSkillRelation(models.Model):
    occupation = models.ForeignKey(
        ESCOOccupationCatalog,
        on_delete=models.CASCADE,
        related_name="skill_relations",
    )

    skill = models.ForeignKey(
        ESCOSkill,
        on_delete=models.CASCADE,
        related_name="occupation_relations",
    )

    relation_type = models.CharField(max_length=32, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["occupation", "skill", "relation_type"],
                name="uniq_esco_occ_skill_relation",
            ),
        ]
        indexes = [
            models.Index(fields=["occupation", "relation_type"]),
            models.Index(fields=["skill", "relation_type"]),
            models.Index(fields=["relation_type"]),
        ]
        ordering = ["occupation_id", "skill_id", "relation_type"]

    def __str__(self):
        return f"{self.occupation_id}:{self.skill_id}:{self.relation_type or 'related'}"


class LLMHierarchyDecision(models.Model):
    cache_key = models.CharField(max_length=64, unique=True)

    profile_hash = models.CharField(max_length=64, db_index=True)

    opportunity = models.ForeignKey(
        "opportunities.Opportunite",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="llm_hierarchy_decisions",
    )

    opportunity_content_hash = models.CharField(max_length=64, db_index=True)

    provider = models.CharField(max_length=64, blank=True, default="")

    model = models.CharField(max_length=128, blank=True, default="")

    is_compatible = models.BooleanField(default=False)

    confidence = models.FloatField(default=0.0)

    issue = models.CharField(max_length=32, blank=True, default="unclear")

    reason = models.CharField(max_length=280, blank=True, default="")

    hierarchy_payload = models.JSONField(default=dict, blank=True)

    response_payload = models.JSONField(default=dict, blank=True)

    hit_count = models.PositiveIntegerField(default=0)

    last_accessed_at = models.DateTimeField(null=True, blank=True)

    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["profile_hash", "opportunity_content_hash"]),
            models.Index(fields=["opportunity", "profile_hash"]),
            models.Index(fields=["provider", "model"]),
            models.Index(fields=["issue", "is_compatible"]),
        ]
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return f"{self.cache_key}:{self.issue}"
