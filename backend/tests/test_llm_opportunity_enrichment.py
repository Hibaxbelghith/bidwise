from __future__ import annotations

from datetime import date, timedelta

from django.test import TestCase

from ai.llm.opportunity_enrichment import (
    enrich_opportunity_with_llm,
    opportunity_needs_llm_enrichment,
)
from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite


class FakeProvider:
    provider_name = "fake"
    model = "fake-model"

    def generate_json(self, prompt, *, schema=None):
        return {
            "target_roles": ["Frontend React Developer"],
            "canonical_role": "Frontend Developer",
            "skills": ["React", "JavaScript", "TypeScript"],
            "tools": ["CSS"],
            "soft_skills": ["Communication", "Autonomy"],
            "domains": ["Frontend development"],
            "business_families": ["frontend"],
            "family_confidence": 0.9,
            "seniority": "junior",
            "experience_level": "JUNIOR",
            "years_experience": 1,
            "years_experience_min": 1,
            "years_experience_max": 2,
            "languages": ["English"],
            "contract_types": ["CDI"],
            "work_modes": ["Remote"],
            "locations": ["Tunis"],
            "salary": "1200-1800 TND",
            "education_level": "Bac+3",
            "responsibilities": ["Create responsive React interfaces"],
            "requirements": ["One year frontend experience"],
            "evidence": ["Create React and TypeScript user interfaces"],
            "warnings": [],
            "confidence": 0.91,
        }


class LLMOpportunityEnrichmentTests(TestCase):
    def setUp(self):
        self.source = SourceOpportunite.objects.create(
            nom="Test source",
            url="https://example.test",
            type_source="SITE_EMPLOI",
        )

    def _opportunity(self, **kwargs):
        defaults = {
            "titre": "Frontend React Developer",
            "description": "Create React and TypeScript user interfaces and responsive layouts.",
            "organisation_nom": "PixelWorks",
            "ville": "Tunis",
            "contract_type": "CDI",
            "availability": "Remote",
            "skills": [],
            "raw_skills": [],
            "normalized_skills": [],
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "date_limite": date.today() + timedelta(days=30),
            "source": self.source,
        }
        defaults.update(kwargs)
        return Opportunite.objects.create(**defaults)

    def test_weak_skill_opportunity_needs_llm_enrichment(self):
        self.assertTrue(opportunity_needs_llm_enrichment(self._opportunity(skills=[])))
        self.assertTrue(opportunity_needs_llm_enrichment(self._opportunity(skills=["Gestion"])))
        self.assertFalse(opportunity_needs_llm_enrichment(self._opportunity(skills=["Gestion", "Reporting"])))

    def test_enrich_opportunity_applies_confident_skills_and_metadata(self):
        opportunity = self._opportunity(skills=[])

        result = enrich_opportunity_with_llm(opportunity.pk, provider=FakeProvider())
        opportunity.refresh_from_db()

        self.assertEqual(result["status"], "updated")
        self.assertTrue(result["applied_to_skills"])
        self.assertEqual(opportunity.skills, ["React", "JavaScript", "TypeScript", "CSS"])
        self.assertEqual(opportunity.raw_skills, ["React", "JavaScript", "TypeScript", "CSS"])
        self.assertIn("llm_enrichment", opportunity.extra_data)
        self.assertTrue(opportunity.extra_data["llm_enrichment"]["applied_to_skills"])
        self.assertEqual(opportunity.extra_data["llm_enrichment"]["business_families"], ["frontend"])

    def test_enrich_opportunity_replaces_existing_skills_when_confident(self):
        opportunity = self._opportunity(skills=["Python", "Django"], raw_skills=["Python", "Django"])

        result = enrich_opportunity_with_llm(opportunity.pk, provider=FakeProvider())
        opportunity.refresh_from_db()

        self.assertEqual(result["status"], "updated")
        self.assertTrue(result["applied_to_skills"])
        self.assertEqual(opportunity.skills, ["React", "JavaScript", "TypeScript", "CSS"])
        self.assertEqual(opportunity.raw_skills, ["React", "JavaScript", "TypeScript", "CSS"])
        self.assertIn("llm_enrichment", opportunity.extra_data)
        metadata = opportunity.extra_data["llm_enrichment"]
        self.assertTrue(metadata["applied_to_skills"])
        self.assertEqual(metadata["skills_source"], "llm")
        self.assertTrue(metadata["replaced_previous_skills"])
        self.assertEqual(metadata["previous_skills"], ["Python", "Django"])

    def test_enrich_opportunity_stores_matching_fields_for_jobbert_text(self):
        opportunity = self._opportunity(
            skills=[],
            experience_min=None,
            experience_max=None,
            education_level="",
            salary="",
        )

        enrich_opportunity_with_llm(opportunity.pk, provider=FakeProvider())
        opportunity.refresh_from_db()

        metadata = opportunity.extra_data["llm_enrichment"]
        self.assertEqual(metadata["canonical_role"], "Frontend Developer")
        self.assertEqual(metadata["family_confidence"], 0.9)
        self.assertEqual(metadata["experience_level"], "JUNIOR")
        self.assertEqual(metadata["years_experience"], 1)
        self.assertEqual(metadata["years_experience_min"], 1)
        self.assertEqual(metadata["years_experience_max"], 2)
        self.assertEqual(metadata["locations"], ["Tunis"])
        self.assertEqual(metadata["salary"], "1200-1800 TND")
        self.assertEqual(metadata["education_level"], "Bac+3")
        self.assertEqual(metadata["responsibilities"], ["Create responsive React interfaces"])
        self.assertEqual(metadata["requirements"], ["One year frontend experience"])
        self.assertEqual(metadata["soft_skills"], ["Communication", "Autonomy"])
        self.assertEqual(opportunity.experience_min, 1)
        self.assertEqual(opportunity.experience_max, 2)
        self.assertEqual(opportunity.education_level, "Bac+3")
        self.assertEqual(opportunity.salary, "1200-1800 TND")


class NoisyAcronymProvider:
    provider_name = "fake"
    model = "fake-model"

    def generate_json(self, prompt, *, schema=None):
        return {
            "target_roles": ["Maintenance Engineer"],
            "canonical_role": "Maintenance Engineer",
            "skills": [
                "GMAO (Global Manufacturing and Asset Optimization)",
                "ERP (Enterprise Resource Planning)",
                "French",
                "Hydraulique",
            ],
            "tools": ["Outils digitaux GMAO"],
            "soft_skills": ["Rigueur"],
            "domains": ["Maintenance poids lourds"],
            "business_families": ["quality_industry"],
            "family_confidence": 0.9,
            "seniority": "mid",
            "experience_level": "CONFIRME",
            "years_experience": 3,
            "languages": ["French"],
            "evidence": ["GMAO ERP Hydraulique"],
            "warnings": [],
            "confidence": 0.9,
        }


class MissingRoleNoisyProvider:
    provider_name = "fake"
    model = "fake-model"

    def generate_json(self, prompt, *, schema=None):
        return {
            "target_roles": [],
            "canonical_role": "",
            "skills": ["French (Français)", "ERP (Enterprise Resource Planning)"],
            "tools": [],
            "soft_skills": ["Communication"],
            "domains": [],
            "business_families": ["other"],
            "family_confidence": 0.0,
            "seniority": "",
            "experience_level": "",
            "years_experience": None,
            "languages": ["French"],
            "evidence": [],
            "warnings": [],
            "confidence": 0.9,
        }


class ThinExtractionProvider:
    provider_name = "fake"
    model = "fake-model"

    def generate_json(self, prompt, *, schema=None):
        return {
            "target_roles": [],
            "canonical_role": "",
            "skills": ["Excel"],
            "tools": [],
            "soft_skills": ["Rigueur"],
            "domains": [],
            "business_families": ["legal_regulatory"],
            "family_confidence": 1.0,
            "seniority": "",
            "experience_level": "",
            "years_experience": None,
            "languages": [],
            "responsibilities": [],
            "requirements": [],
            "evidence": [],
            "warnings": ["thin_extraction"],
            "confidence": 1.0,
        }


class ResponsibilityOnlyWeakSkillProvider:
    provider_name = "fake"
    model = "fake-model"

    def generate_json(self, prompt, *, schema=None):
        return {
            "target_roles": ["Agent de sécurité"],
            "canonical_role": "Agent de sécurité",
            "skills": ["Observation"],
            "tools": [],
            "soft_skills": ["Réactivité", "Rigueur"],
            "domains": [],
            "business_families": ["security_safety"],
            "family_confidence": 0.9,
            "seniority": "junior",
            "experience_level": "JUNIOR",
            "years_experience": 1,
            "languages": [],
            "responsibilities": [
                "Surveiller les lieux et assurer une présence sécuritaire",
                "Faire appliquer les procédures de sécurité",
            ],
            "requirements": ["Une première expérience dans la sécurité est souhaitée"],
            "evidence": ["Surveiller les lieux"],
            "warnings": [],
            "confidence": 0.95,
        }


class MedicalSecretaryProvider:
    provider_name = "fake"
    model = "fake-model"

    def generate_json(self, prompt, *, schema=None):
        return {
            "target_roles": ["Secrétaire Médicale"],
            "canonical_role": "Secrétaire Médicale Cabinet d'Endodontie",
            "skills": ["Discrétion", "Confidentialité", "Maîtrise des outils bureautiques"],
            "tools": [],
            "soft_skills": ["Sens de l'accueil"],
            "domains": ["santé / paramédical / optique"],
            "business_families": ["hr_administration"],
            "family_confidence": 0.8,
            "seniority": "junior",
            "experience_level": "JUNIOR",
            "years_experience": 2,
            "languages": [],
            "responsibilities": [
                "Accueil physique et téléphonique des patients",
                "Gestion des rendez-vous et du planning du praticien",
                "Constitution et suivi des dossiers patients",
            ],
            "requirements": ["Formation en secrétariat médical ou administratif souhaitée"],
            "evidence": ["cabinet d'endodontie", "patients"],
            "warnings": [],
            "confidence": 0.8,
        }


class AdministrativeFinanceProvider:
    provider_name = "fake"
    model = "fake-model"

    def generate_json(self, prompt, *, schema=None):
        return {
            "target_roles": ["Assistante Administrative et Financière"],
            "canonical_role": "Assistante Administrative et Financière",
            "skills": ["Excel", "Word"],
            "tools": [],
            "soft_skills": ["Rigueur", "Relationnel"],
            "domains": [],
            "business_families": ["accounting_finance_audit"],
            "family_confidence": 0.8,
            "seniority": "junior",
            "experience_level": "JUNIOR",
            "years_experience": 2,
            "languages": [],
            "responsibilities": [
                "Préparer les relevés de facturation client",
                "Assurer la relation avec la banque",
                "Soutien administratif de la direction",
            ],
            "requirements": ["Formation supérieure en Finance ou Comptabilité"],
            "evidence": ["Assistante Administrative et Financière"],
            "warnings": [],
            "confidence": 0.8,
        }


class TechnicalSupportActionProvider:
    provider_name = "fake"
    model = "fake-model"

    def generate_json(self, prompt, *, schema=None):
        return {
            "target_roles": ["Technicien Réseau"],
            "canonical_role": "Technicien Réseau et Maintenance Informatique",
            "skills": ["Réseau", "Maintenance informatique"],
            "tools": [],
            "soft_skills": ["Diagnostiquer", "Résoudre incidents", "Installer", "Rigueur"],
            "domains": [],
            "business_families": ["it_network_support"],
            "family_confidence": 1.0,
            "seniority": "",
            "experience_level": "",
            "years_experience": 2,
            "languages": [],
            "responsibilities": [
                "Diagnostiquer et résoudre les incidents techniques",
                "Installer et sécuriser les infrastructures réseau",
            ],
            "requirements": ["Bac+2 ou Bac+3"],
            "evidence": ["réseau et maintenance informatique"],
            "warnings": [],
            "confidence": 1.0,
        }


class LLMOpportunityEnrichmentCleanupTests(TestCase):
    def setUp(self):
        self.source = SourceOpportunite.objects.create(
            nom="Test source",
            url="https://example.test",
            type_source="SITE_EMPLOI",
        )

    def test_enrichment_filters_language_skills_and_unverified_acronym_expansions(self):
        opportunity = Opportunite.objects.create(
            titre="Ingenieur maintenance camions et engins",
            description="Maintenance poids lourds, hydraulique, GMAO, ERP et reporting maintenance.",
            organisation_nom="FleetCo",
            ville="Tunis",
            skills=[],
            raw_skills=[],
            normalized_skills=[],
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            date_limite=date.today() + timedelta(days=30),
            source=self.source,
        )

        result = enrich_opportunity_with_llm(opportunity.pk, provider=NoisyAcronymProvider())
        opportunity.refresh_from_db()

        self.assertEqual(result["status"], "updated")
        self.assertIn("GMAO", opportunity.skills)
        self.assertIn("ERP", opportunity.skills)
        self.assertIn("Hydraulique", opportunity.skills)
        self.assertNotIn("French", opportunity.skills)
        self.assertNotIn("GMAO (Global Manufacturing and Asset Optimization)", opportunity.skills)
        self.assertNotIn("ERP (Enterprise Resource Planning)", opportunity.skills)
        self.assertEqual(result["canonical_role"], "Maintenance Engineer")

    def test_enrichment_falls_back_to_title_when_ollama_omits_role(self):
        opportunity = Opportunite.objects.create(
            titre="Responsable Affaires Reglementaires",
            description="Suivi des dossiers reglementaires avec ERP.",
            organisation_nom="RegCo",
            ville="Tunis",
            skills=[],
            raw_skills=[],
            normalized_skills=[],
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            date_limite=date.today() + timedelta(days=30),
            source=self.source,
        )

        result = enrich_opportunity_with_llm(opportunity.pk, provider=MissingRoleNoisyProvider())
        opportunity.refresh_from_db()

        self.assertEqual(result["canonical_role"], "Responsable Affaires Reglementaires")
        self.assertEqual(opportunity.extra_data["llm_enrichment"]["canonical_role"], "Responsable Affaires Reglementaires")
        self.assertFalse(result["applied_to_skills"])
        self.assertEqual(opportunity.skills, [])
        self.assertIn("ERP (Enterprise Resource Planning)", opportunity.extra_data["llm_enrichment"]["skills"])
        self.assertNotIn("French", opportunity.skills)

    def test_thin_extraction_is_stored_but_not_applied_to_skills(self):
        opportunity = Opportunite.objects.create(
            titre="Responsable Affaires Reglementaires",
            description="Suivi des dossiers reglementaires et coordination administrative.",
            organisation_nom="RegCo",
            ville="Tunis",
            skills=["Reglementation"],
            raw_skills=["Reglementation"],
            normalized_skills=[],
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            date_limite=date.today() + timedelta(days=30),
            source=self.source,
        )

        result = enrich_opportunity_with_llm(opportunity.pk, provider=ThinExtractionProvider())
        opportunity.refresh_from_db()

        self.assertFalse(result["applied_to_skills"])
        self.assertEqual(opportunity.skills, ["Reglementation"])
        self.assertEqual(opportunity.extra_data["llm_enrichment"]["skills"], ["Excel"])
        self.assertFalse(opportunity.extra_data["llm_enrichment"]["applied_to_skills"])

    def test_responsibilities_alone_do_not_apply_weak_skill_labels(self):
        opportunity = Opportunite.objects.create(
            titre="Agent de sécurité",
            description=(
                "Veiller à la sécurité des personnes et des biens. Surveiller les lieux. "
                "Faire appliquer les procédures de sécurité. Bonne observation et rigueur."
            ),
            organisation_nom="SecureCo",
            ville="Tunis",
            skills=[],
            raw_skills=[],
            normalized_skills=[],
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            date_limite=date.today() + timedelta(days=30),
            source=self.source,
        )

        result = enrich_opportunity_with_llm(opportunity.pk, provider=ResponsibilityOnlyWeakSkillProvider())
        opportunity.refresh_from_db()

        self.assertFalse(result["applied_to_skills"])
        self.assertEqual(opportunity.skills, [])
        metadata = opportunity.extra_data["llm_enrichment"]
        self.assertEqual(metadata["business_families"], ["security_safety"])
        self.assertEqual(metadata["responsibilities"][0], "Surveiller les lieux et assurer une présence sécuritaire")
        self.assertFalse(metadata["applied_to_skills"])

    def test_post_validation_reclassifies_medical_secretary_as_healthcare_admin(self):
        opportunity = Opportunite.objects.create(
            titre="Secrétaire Médicale Cabinet d'Endodontie",
            description=(
                "Accueil des patients, gestion des rendez-vous, constitution des dossiers patients "
                "et coordination avec l'équipe soignante dans un cabinet dentaire."
            ),
            organisation_nom="DentalCare",
            ville="Tunis",
            skills=[],
            raw_skills=[],
            normalized_skills=[],
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            date_limite=date.today() + timedelta(days=30),
            source=self.source,
            extra_data={"company_sector": "santé / paramédical / optique"},
        )

        result = enrich_opportunity_with_llm(opportunity.pk, provider=MedicalSecretaryProvider())
        opportunity.refresh_from_db()

        metadata = opportunity.extra_data["llm_enrichment"]
        self.assertIn("healthcare", metadata["business_families"])
        self.assertIn("administration", metadata["business_families"])
        self.assertNotIn("hr_administration", metadata["business_families"])
        self.assertNotIn("customer_support", metadata["business_families"])
        self.assertNotIn("accounting_finance_audit", metadata["business_families"])
        self.assertIn("post_validation_removed_hr_for_medical_admin", metadata["warnings"])
        self.assertIn("Discrétion", metadata["soft_skills"])
        self.assertNotIn("Discrétion", metadata["skills"])
        self.assertEqual(result["business_families"], metadata["business_families"])

    def test_post_validation_keeps_admin_family_for_admin_finance_role(self):
        opportunity = Opportunite.objects.create(
            titre="Assistante Administrative et Financière",
            description=(
                "Préparer les relevés de facturation client, gérer les règlements fournisseurs, "
                "assurer la relation avec la banque et soutenir les tâches administratives."
            ),
            organisation_nom="Active",
            ville="Tunis",
            skills=[],
            raw_skills=[],
            normalized_skills=[],
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            date_limite=date.today() + timedelta(days=30),
            source=self.source,
        )

        enrich_opportunity_with_llm(opportunity.pk, provider=AdministrativeFinanceProvider())
        opportunity.refresh_from_db()

        metadata = opportunity.extra_data["llm_enrichment"]
        self.assertIn("accounting_finance_audit", metadata["business_families"])
        self.assertIn("administration", metadata["business_families"])
        self.assertNotIn("customer_support", metadata["business_families"])
        self.assertIn("post_validation_added_family:administration", metadata["warnings"])

    def test_post_validation_moves_technical_actions_out_of_soft_skills(self):
        opportunity = Opportunite.objects.create(
            titre="Technicien Réseau et Maintenance Informatique",
            description=(
                "Diagnostiquer et résoudre les incidents techniques. Installer et sécuriser "
                "les infrastructures réseau et fournir un support technique aux utilisateurs."
            ),
            organisation_nom="ITCo",
            ville="Tunis",
            skills=[],
            raw_skills=[],
            normalized_skills=[],
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            date_limite=date.today() + timedelta(days=30),
            source=self.source,
        )

        enrich_opportunity_with_llm(opportunity.pk, provider=TechnicalSupportActionProvider())
        opportunity.refresh_from_db()

        metadata = opportunity.extra_data["llm_enrichment"]
        self.assertIn("Diagnostiquer", metadata["skills"])
        self.assertIn("Résoudre incidents", metadata["skills"])
        self.assertNotIn("Diagnostiquer", metadata["soft_skills"])
        self.assertIn("Rigueur", metadata["soft_skills"])
        self.assertIn("post_validation_moved_action_to_skill:Diagnostiquer", metadata["warnings"])
