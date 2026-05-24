from datetime import date
from io import StringIO
from types import SimpleNamespace

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, SimpleTestCase
from rest_framework.test import APIClient

from opportunities.autocomplete.indexer import build_profile_suggestion_index
from opportunities.autocomplete.service import normalize_profile_terms, suggest_profile_terms
from opportunities.extraction.profile_terms import (
    classify_profile_term,
    extract_interest_terms,
    extract_role_terms,
    extract_skill_terms,
    is_rejected_profile_term,
)
from opportunities.normalization.industries import normalize_industries
from opportunities.models import (
    Opportunite,
    ProfileSuggestion,
    ProfileSuggestionType,
    SourceOpportunite,
    StatutOpportunite,
    TypeOpportunite,
)
from opportunities.normalization.text import normalize_lookup_key
from users.models import Utilisateur
from users.serializers import ProfilUpdateSerializer


class MultilingualTextNormalizationTests(SimpleTestCase):
    def test_lookup_key_is_accent_and_arabic_safe(self):
        self.assertEqual(normalize_lookup_key("Développeur Front-End"), "developpeur front end")
        self.assertEqual(normalize_lookup_key("إدارة الأعمال"), "اداره الاعمال")
        self.assertEqual(normalize_lookup_key("React.js / CSS3"), "react js css3")
        self.assertEqual(normalize_lookup_key("تــرْبص"), "تربص")


class ProfileTermExtractionTests(SimpleTestCase):
    def test_role_extraction_collapses_frontend_variants(self):
        opportunity = SimpleNamespace(
            type_opportunite=TypeOpportunite.EMPLOI,
            titre="Senior Front-End Developer - Tunis",
        )

        terms = extract_role_terms(opportunity)

        self.assertEqual(terms[0].canonical, "Frontend Developer")
        self.assertIn("Senior Front-End Developer - Tunis", terms[0].aliases)

    def test_french_accented_role_variants_canonicalize(self):
        opportunity = SimpleNamespace(
            type_opportunite=TypeOpportunite.EMPLOI,
            titre="Développeur Full Stack",
        )

        terms = extract_role_terms(opportunity)

        self.assertEqual(terms[0].canonical, "Full Stack Developer")

    def test_arabic_internship_role_canonicalizes(self):
        opportunity = SimpleNamespace(
            type_opportunite=TypeOpportunite.STAGE,
            titre="تربص تطوير واجهات",
        )

        terms = extract_role_terms(opportunity)

        self.assertEqual(terms[0].canonical, "Frontend Developer")

    def test_rejects_noisy_generic_and_cross_type_roles(self):
        for title in ("Developer", "Engineer", "Senior", "Front", "Backend", "React", "Urgent", "Tunis", "H/F"):
            opportunity = SimpleNamespace(
                type_opportunite=TypeOpportunite.EMPLOI,
                titre=title,
            )
            self.assertEqual(extract_role_terms(opportunity), [])

        self.assertTrue(is_rejected_profile_term(ProfileSuggestionType.ROLE, "Front"))

    def test_skill_extraction_uses_structured_and_alias_signals(self):
        opportunity = SimpleNamespace(
            titre="Software Engineer",
            description="We use React.js, JS and Python for analytics.",
            skills=["Py", "React.js"],
            extra_data={"job_qualifications": "SQL and Power BI are a plus."},
        )

        canonical = {term.canonical for term in extract_skill_terms(opportunity)}

        self.assertIn("Python", canonical)
        self.assertIn("React", canonical)
        self.assertIn("SQL", canonical)
        self.assertIn("Power BI", canonical)

    def test_skill_canonicalization_and_role_separation(self):
        opportunity = SimpleNamespace(
            titre="Software Engineer",
            description="CSS3 and ReactJS role",
            skills=["css3", "Software Engineer"],
            extra_data={},
        )

        canonical = {term.canonical for term in extract_skill_terms(opportunity)}

        self.assertIn("CSS", canonical)
        self.assertNotIn("Software Engineer", canonical)

    def test_generic_domains_topics_and_roles_do_not_become_skills(self):
        opportunity = SimpleNamespace(
            titre="Frontend Developer",
            description="Santé Machines Mission Poste Commercial CSS React",
            skills=["Santé", "Machines", "Mission", "Poste", "Commercial", "css"],
            extra_data={},
        )

        canonical = {term.canonical for term in extract_skill_terms(opportunity)}

        self.assertEqual(classify_profile_term("CSS"), "HARD_SKILL")
        self.assertEqual(classify_profile_term("Frontend Developer"), "ROLE")
        self.assertEqual(classify_profile_term("Santé"), "DOMAIN")
        self.assertEqual(classify_profile_term("Mission"), "NOISE")
        self.assertIn("CSS", canonical)
        self.assertNotIn("Santé", canonical)
        self.assertNotIn("Machines", canonical)
        self.assertNotIn("Mission", canonical)
        self.assertNotIn("Poste", canonical)
        self.assertNotIn("Commercial", canonical)

    def test_company_sector_maps_to_normalized_interest(self):
        opportunity = SimpleNamespace(
            normalized_industries=[],
            extra_data={"company_sector": "Sante, pharmacie, hopitaux, equipements medicaux"},
        )

        terms = extract_interest_terms(opportunity)

        self.assertEqual([term.canonical for term in terms], ["HEALTHCARE"])
        self.assertEqual(normalize_industries("banque; assurance"), ["FINTECH"])


class ProfileAutocompleteIndexTests(TestCase):
    def setUp(self):
        cache.clear()
        self.source = SourceOpportunite.objects.create(
            nom="TestSource",
            url="https://example.com",
            type_source="SITE_EMPLOI",
        )
        self.user = Utilisateur.objects.create_user(
            username="autocomplete-user",
            email="autocomplete@example.com",
            password="pass1234",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def tearDown(self):
        cache.clear()

    def _create_opportunity(self, **overrides):
        payload = {
            "titre": "Développeur Frontend - Tunis",
            "description": "React.js, JS, Python, SQL and communication are required.",
            "skills": ["React.js", "Py"],
            "extra_data": {"job_qualifications": "Power BI and Excel are a plus."},
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date(2026, 1, 1),
            "source": self.source,
        }
        payload.update(overrides)
        return Opportunite.objects.create(**payload)

    def test_indexer_persists_role_and_skill_suggestions(self):
        self._create_opportunity()
        self._create_opportunity()

        result = build_profile_suggestion_index()

        self.assertGreaterEqual(result["kept"], 2)
        self.assertTrue(
            ProfileSuggestion.objects.filter(
                term_type=ProfileSuggestionType.ROLE,
                canonical="Frontend Developer",
                is_active=True,
            ).exists()
        )
        self.assertTrue(
            ProfileSuggestion.objects.filter(
                term_type=ProfileSuggestionType.SKILL,
                canonical="Python",
                is_active=True,
            ).exists()
        )

    def test_suggestion_service_ranks_prefix_and_alias_matches(self):
        self._create_opportunity()
        self._create_opportunity()
        build_profile_suggestion_index()

        skill_payload = suggest_profile_terms(ProfileSuggestionType.SKILL, "rea", limit=5)
        role_payload = suggest_profile_terms(ProfileSuggestionType.ROLE, "developpeur", limit=5)

        self.assertEqual(skill_payload["results"][0]["value"], "React")
        self.assertEqual(role_payload["results"][0]["value"], "Frontend Developer")

    def test_role_token_keys_do_not_include_title_context_noise(self):
        self._create_opportunity(
            titre="Monteur Video / Video Editor - Agence Marketing (Teletravail)",
            description="Montage video pour une agence.",
            skills=[],
        )
        self._create_opportunity(
            titre="Monteur Video / Video Editor - Studio de production (Teletravail)",
            description="Montage video pour un studio.",
            skills=[],
        )
        build_profile_suggestion_index()

        role = ProfileSuggestion.objects.get(
            term_type=ProfileSuggestionType.ROLE,
            canonical="Monteur Video Video Editor",
        )
        self.assertNotIn("marketing", role.metadata.get("token_keys", []))

        payload = suggest_profile_terms(ProfileSuggestionType.ROLE, "marketing", limit=5)
        self.assertEqual(payload["results"], [])

    def test_role_autocomplete_supports_tokenized_accent_insensitive_queries(self):
        for canonical, aliases in (
            ("Frontend Developer", ["Développeur Frontend", "Front-End Developer"]),
            ("Backend Developer", ["Développeur Backend", "Back-End Developer"]),
            ("Full Stack Developer", ["Développeur Full Stack", "Full-Stack Developer"]),
        ):
            ProfileSuggestion.objects.create(
                term_type=ProfileSuggestionType.ROLE,
                canonical=canonical,
                normalized_key=normalize_lookup_key(canonical),
                aliases=aliases,
                frequency=5,
                confidence=0.94,
            )

        expectations = {
            "frontend": "Frontend Developer",
            "backend": "Backend Developer",
            "fullstack": "Full Stack Developer",
            "développeur": "Backend Developer",
            "developpeur": "Backend Developer",
        }
        for query, expected in expectations.items():
            payload = suggest_profile_terms(ProfileSuggestionType.ROLE, query, limit=5)
            values = [item["value"] for item in payload["results"]]
            self.assertIn(expected, values)

    def test_indexer_stores_role_token_and_compact_keys(self):
        self._create_opportunity(titre="Frontend Developer")
        self._create_opportunity(titre="Frontend Developer")

        build_profile_suggestion_index()

        suggestion = ProfileSuggestion.objects.get(
            term_type=ProfileSuggestionType.ROLE,
            canonical="Frontend Developer",
        )
        self.assertIn("frontend", suggestion.metadata["alias_keys"])
        self.assertIn("front end", suggestion.metadata["alias_keys"])
        self.assertIn("frontend", suggestion.metadata["compact_keys"])
        self.assertIn("frontend", suggestion.metadata["token_keys"])

    def test_role_autocomplete_keeps_fuzzy_conservative(self):
        ProfileSuggestion.objects.create(
            term_type=ProfileSuggestionType.ROLE,
            canonical="Frontend Developer",
            normalized_key=normalize_lookup_key("Frontend Developer"),
            aliases=["Front-End Developer"],
            frequency=5,
            confidence=0.94,
        )

        payload = suggest_profile_terms(ProfileSuggestionType.ROLE, "frint", limit=5)

        self.assertEqual(payload["results"], [])

    def test_profile_suggestion_api_returns_ranked_results(self):
        self._create_opportunity()
        self._create_opportunity()
        build_profile_suggestion_index()

        response = self.client.get("/api/profile/skills/suggest/?q=py&limit=3")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["type"], "skill")
        self.assertEqual(response.data["results"][0]["value"], "Python")

    def test_interest_autocomplete_uses_taxonomy_and_company_sector(self):
        self._create_opportunity(extra_data={"company_sector": "Sante, pharmacie"})
        self._create_opportunity(extra_data={"company_sector": "Sante, pharmacie"})
        build_profile_suggestion_index()

        response = self.client.get("/api/profile/interests/suggest/?q=hea&limit=3")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["type"], "interest")
        self.assertEqual(response.data["results"][0]["value"], "HEALTHCARE")

    def test_interest_autocomplete_has_dictionary_hot_path(self):
        payload = suggest_profile_terms(ProfileSuggestionType.INTEREST, "fin", limit=5)

        self.assertEqual(payload["results"][0]["value"], "FINTECH")

    def test_profile_serializer_canonicalizes_known_aliases_and_preserves_unknowns(self):
        ProfileSuggestion.objects.create(
            term_type=ProfileSuggestionType.SKILL,
            canonical="Python",
            normalized_key=normalize_lookup_key("Python"),
            aliases=["Py", "python"],
            frequency=10,
            confidence=0.95,
        )
        ProfileSuggestion.objects.create(
            term_type=ProfileSuggestionType.ROLE,
            canonical="Frontend Developer",
            normalized_key=normalize_lookup_key("Frontend Developer"),
            aliases=["Développeur Frontend"],
            frequency=8,
            confidence=0.9,
        )

        serializer = ProfilUpdateSerializer(
            self.user.profil,
            data={
                "competences": ["Py", "Python", "Custom Skill"],
                "target_roles": ["Développeur Frontend"],
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        profile = serializer.save()
        self.assertEqual(profile.competences, ["Python", "Custom Skill"])
        self.assertEqual(profile.target_roles, ["Frontend Developer"])

    def test_profile_serializer_canonicalizes_interests_and_rejects_skills_or_roles(self):
        serializer = ProfilUpdateSerializer(
            self.user.profil,
            data={
                "domaines_interet": ["sante", "React", "Backend Developer", "e-commerce"],
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        profile = serializer.save()
        self.assertEqual(profile.domaines_interet, ["HEALTHCARE", "ECOMMERCE"])

    def test_profile_serializer_filters_polluted_target_roles(self):
        serializer = ProfilUpdateSerializer(
            self.user.profil,
            data={
                "target_roles": ["Frontend Developer", "Front", "React"],
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        profile = serializer.save()
        self.assertEqual(profile.target_roles, ["Frontend Developer"])

    def test_profile_cleanup_command_canonicalizes_and_preserves_valid_custom_values(self):
        profile = self.user.profil
        profile.competences = ["React", "JavaScript", "Python", "css", "Custom Skill"]
        profile.domaines_interet = ["sante", "React", "Backend Developer"]
        profile.target_roles = [
            "Frontend Developer",
            "Front",
            "React",
            "Développeur Frontend",
            "Urbaniste",
        ]
        profile.embedding = [0.1, 0.2]
        profile.embedding_features_hash = "dirty"
        profile.save()

        out = StringIO()
        call_command("clean_profile_terms", stdout=out)

        profile.refresh_from_db()
        self.assertEqual(profile.competences, ["React", "JavaScript", "Python", "CSS", "Custom Skill"])
        self.assertEqual(profile.domaines_interet, ["HEALTHCARE"])
        self.assertEqual(profile.target_roles, ["Frontend Developer", "Urbaniste"])
        self.assertIsNone(profile.embedding)
        self.assertEqual(profile.embedding_features_hash, "")
        self.assertIn("changed: 1", out.getvalue())

    def test_profile_cleanup_command_dry_run_does_not_write(self):
        profile = self.user.profil
        profile.competences = ["css", "js", "py"]
        profile.domaines_interet = ["sante", "React"]
        profile.target_roles = ["Frontend Developer", "Front", "React"]
        profile.save()

        out = StringIO()
        call_command("clean_profile_terms", "--dry-run", stdout=out)

        profile.refresh_from_db()
        self.assertEqual(profile.competences, ["css", "js", "py"])
        self.assertEqual(profile.domaines_interet, ["sante", "React"])
        self.assertEqual(profile.target_roles, ["Frontend Developer", "Front", "React"])
        self.assertIn("dry_run: True", out.getvalue())
        self.assertIn("changed: 1", out.getvalue())

    def test_profile_term_normalization_canonicalizes_skill_aliases(self):
        normalized = normalize_profile_terms(
            ProfileSuggestionType.SKILL,
            ["css", "js", "py", "react.js", "nodejs"],
        )

        self.assertEqual(normalized, ["CSS", "JavaScript", "Python", "React", "Node.js"])

    def test_dictionary_alias_autocomplete_canonicalizes_without_index_row(self):
        payload = suggest_profile_terms(ProfileSuggestionType.SKILL, "css", limit=5)

        self.assertEqual(payload["results"][0]["value"], "CSS")

    def test_alias_merging_keeps_one_semantic_skill(self):
        self._create_opportunity(skills=["ReactJS"], description="ReactJS")
        self._create_opportunity(skills=["React.js"], description="React.js")

        build_profile_suggestion_index()

        suggestions = ProfileSuggestion.objects.filter(
            term_type=ProfileSuggestionType.SKILL,
            canonical="React",
            is_active=True,
        )
        self.assertEqual(suggestions.count(), 1)
        suggestion = suggestions.get()
        self.assertEqual(suggestion.frequency, 2)
        self.assertIn("reactjs", suggestion.metadata["alias_keys"])
        self.assertIn("react js", suggestion.metadata["alias_keys"])

    def test_inactive_opportunities_do_not_feed_index(self):
        self._create_opportunity(statut=StatutOpportunite.ARCHIVEE)

        build_profile_suggestion_index()

        self.assertFalse(ProfileSuggestion.objects.exists())

    def test_stale_suggestions_are_deactivated(self):
        self._create_opportunity(skills=["ReactJS"], description="ReactJS")
        self._create_opportunity(skills=["React.js"], description="React.js")
        build_profile_suggestion_index()
        self.assertTrue(ProfileSuggestion.objects.filter(canonical="React", is_active=True).exists())

        Opportunite.objects.update(statut=StatutOpportunite.ARCHIVEE)
        build_profile_suggestion_index()

        self.assertTrue(ProfileSuggestion.objects.filter(canonical="React", is_active=False).exists())

    def test_front_returns_frontend_not_urbaniste(self):
        ProfileSuggestion.objects.create(
            term_type=ProfileSuggestionType.ROLE,
            canonical="Frontend Developer",
            normalized_key=normalize_lookup_key("Frontend Developer"),
            aliases=["Développeur Frontend", "Front-End Developer"],
            frequency=4,
            confidence=0.92,
        )
        ProfileSuggestion.objects.create(
            term_type=ProfileSuggestionType.ROLE,
            canonical="Urbaniste",
            normalized_key=normalize_lookup_key("Urbaniste"),
            aliases=["Urban Planner"],
            frequency=50,
            confidence=0.96,
        )

        payload = suggest_profile_terms(ProfileSuggestionType.ROLE, "front", limit=5)
        values = [item["value"] for item in payload["results"]]

        self.assertEqual(values[0], "Frontend Developer")
        self.assertNotIn("Urbaniste", values)

    def test_polluted_role_rows_are_not_served(self):
        for canonical in ("React", "Front"):
            ProfileSuggestion.objects.create(
                term_type=ProfileSuggestionType.ROLE,
                canonical=canonical,
                normalized_key=normalize_lookup_key(canonical),
                aliases=[canonical],
                frequency=50,
                confidence=0.99,
            )

        react_payload = suggest_profile_terms(ProfileSuggestionType.ROLE, "react", limit=5)
        front_payload = suggest_profile_terms(ProfileSuggestionType.ROLE, "front", limit=5)

        self.assertEqual(react_payload["results"], [])
        self.assertEqual(front_payload["results"], [])

    def test_rea_returns_react_before_unrelated_fuzzy_results(self):
        ProfileSuggestion.objects.create(
            term_type=ProfileSuggestionType.SKILL,
            canonical="React",
            normalized_key=normalize_lookup_key("React"),
            aliases=["ReactJS", "React.js"],
            frequency=4,
            confidence=0.94,
        )
        ProfileSuggestion.objects.create(
            term_type=ProfileSuggestionType.SKILL,
            canonical="Reporting",
            normalized_key=normalize_lookup_key("Reporting"),
            aliases=["Reports"],
            frequency=50,
            confidence=0.92,
        )

        payload = suggest_profile_terms(ProfileSuggestionType.SKILL, "rea", limit=5)

        self.assertEqual(payload["results"][0]["value"], "React")

    def test_typo_tolerance_is_conservative(self):
        ProfileSuggestion.objects.create(
            term_type=ProfileSuggestionType.SKILL,
            canonical="React",
            normalized_key=normalize_lookup_key("React"),
            aliases=["ReactJS"],
            frequency=4,
            confidence=0.94,
        )

        payload = suggest_profile_terms(ProfileSuggestionType.SKILL, "recat", limit=5)

        self.assertEqual(payload["results"][0]["value"], "React")
        self.assertEqual(payload["results"][0]["match"], "fuzzy")

    def test_frequency_filtering_removes_singletons(self):
        ProfileSuggestion.objects.create(
            term_type=ProfileSuggestionType.SKILL,
            canonical="React",
            normalized_key=normalize_lookup_key("React"),
            aliases=["ReactJS"],
            frequency=1,
            confidence=0.94,
        )
        ProfileSuggestion.objects.create(
            term_type=ProfileSuggestionType.SKILL,
            canonical="Python",
            normalized_key=normalize_lookup_key("Python"),
            aliases=["Py"],
            frequency=2,
            confidence=0.94,
        )

        payload = suggest_profile_terms(ProfileSuggestionType.SKILL, "", limit=5)
        values = [item["value"] for item in payload["results"]]

        self.assertEqual(values, ["Python"])

    def test_suggestion_service_uses_one_query_then_cache(self):
        ProfileSuggestion.objects.create(
            term_type=ProfileSuggestionType.SKILL,
            canonical="React",
            normalized_key=normalize_lookup_key("React"),
            aliases=["ReactJS"],
            frequency=3,
            confidence=0.94,
        )
        cache.clear()

        with self.assertNumQueries(1):
            suggest_profile_terms(ProfileSuggestionType.SKILL, "rea", limit=5)
        with self.assertNumQueries(0):
            suggest_profile_terms(ProfileSuggestionType.SKILL, "rea", limit=5)
