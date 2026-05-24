from django.test import TestCase

from ai.hierarchy_llm import (
    LLMHierarchyValidation,
    build_hierarchy_validation_cache_key,
    build_opportunity_content_hash,
    get_cached_hierarchy_decision,
    store_hierarchy_decision,
)
from ai.models import LLMHierarchyDecision


class LLMHierarchyDecisionCacheTests(TestCase):
    def test_store_and_read_cached_hierarchy_decision(self):
        hierarchy_validation = {
            "needs_llm": True,
            "hierarchy_issue": "none",
            "seniority_gap": 1,
        }
        content_hash = build_opportunity_content_hash(
            opportunity_title="Comptable Confirme",
            opportunity_description="Comptabilite et fiscalite.",
            opportunity_skills=["comptabilite", "fiscalite"],
        )
        cache_key = build_hierarchy_validation_cache_key(
            profile_text="Role: Comptable junior.",
            opportunity_id=999999,
            opportunity_content_hash=content_hash,
            hierarchy_validation=hierarchy_validation,
        )

        store_hierarchy_decision(
            cache_key=cache_key,
            profile_text="Role: Comptable junior.",
            opportunity_id=999999,
            opportunity_content_hash=content_hash,
            hierarchy_validation=hierarchy_validation,
            result=LLMHierarchyValidation(
                is_compatible=False,
                confidence=0.82,
                issue="seniority_gap",
                reason="Offre plus senior que le profil.",
                provider="fake",
                model="fake-model",
                cache_key=cache_key,
            ),
        )

        cached = get_cached_hierarchy_decision(cache_key)

        self.assertIsNotNone(cached)
        self.assertFalse(cached.is_compatible)
        self.assertEqual(cached.issue, "seniority_gap")
        self.assertEqual(cached.provider, "fake")
        self.assertEqual(LLMHierarchyDecision.objects.get(cache_key=cache_key).hit_count, 1)

    def test_opportunity_content_hash_changes_when_offer_changes(self):
        first = build_opportunity_content_hash(
            opportunity_title="IT Helpdesk Officer",
            opportunity_description="Support Windows.",
            opportunity_skills=["Windows"],
        )
        second = build_opportunity_content_hash(
            opportunity_title="IT Helpdesk Officer",
            opportunity_description="Support Windows and Active Directory.",
            opportunity_skills=["Windows"],
        )

        self.assertNotEqual(first, second)
