from django.db import models


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
