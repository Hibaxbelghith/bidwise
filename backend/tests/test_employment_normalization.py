from django.test import SimpleTestCase

from opportunities.normalization.employment import (
    CONTRACT_TYPE_ALTERNANCE,
    CONTRACT_TYPE_CDD,
    CONTRACT_TYPE_CDI,
    CONTRACT_TYPE_FREELANCE,
    CONTRACT_TYPE_INTERNSHIP,
    CONTRACT_TYPE_PUBLIC_SECTOR,
    CONTRACT_TYPE_SEASONAL,
    CONTRACT_TYPE_SIVP,
    CONTRACT_TYPE_TEMPORARY_INTERIM,
    SCHEDULE_FULL_TIME,
    SCHEDULE_PART_TIME,
    SCHEDULE_UNSPECIFIED,
    WORK_MODE_HYBRID,
    WORK_MODE_ON_SITE,
    WORK_MODE_REMOTE,
    WORK_MODE_UNSPECIFIED,
    normalize_contract_type,
    normalize_contract_types,
    normalize_contract_values,
    normalize_key,
    normalize_schedule,
    normalize_work_mode,
    split_contract_values,
)


class EmploymentNormalizationTests(SimpleTestCase):
    def test_normalize_key_is_case_and_accent_insensitive(self):
        self.assertEqual(normalize_key("  Télétravail  "), "teletravail")
        self.assertEqual(normalize_key("Indépendant/Freelance"), "independant freelance")

    def test_split_contract_values_supports_multi_value_strings(self):
        self.assertEqual(
            split_contract_values("CDI - CDD - Stage/PFE"),
            ["CDI", "CDD", "Stage", "PFE"],
        )

    def test_normalize_contract_types_deduplicates_canonical_values(self):
        self.assertEqual(
            normalize_contract_types("CDI - cdd - Stage - Internship - SIVP"),
            [
                CONTRACT_TYPE_CDI,
                CONTRACT_TYPE_CDD,
                CONTRACT_TYPE_INTERNSHIP,
                CONTRACT_TYPE_SIVP,
            ],
        )

    def test_normalize_contract_types_handles_tunisian_market_values(self):
        self.assertEqual(normalize_contract_types("Indépendant/Freelance"), [CONTRACT_TYPE_FREELANCE])
        self.assertEqual(normalize_contract_types("Alternance"), [CONTRACT_TYPE_ALTERNANCE])
        self.assertEqual(normalize_contract_types("Intérim"), [CONTRACT_TYPE_TEMPORARY_INTERIM])
        self.assertEqual(normalize_contract_types("Saisonnier"), [CONTRACT_TYPE_SEASONAL])
        self.assertEqual(normalize_contract_types("Fonction publique"), [CONTRACT_TYPE_PUBLIC_SECTOR])

    def test_normalize_contract_types_ignores_schedule_and_work_mode_noise(self):
        self.assertEqual(
            normalize_contract_types("CDI - Temps partiel - Remote"),
            [CONTRACT_TYPE_CDI],
        )

    def test_normalize_contract_values_preserves_unknowns_separately(self):
        result = normalize_contract_values("CDI - Contrat spécial - Contrat spécial")

        self.assertEqual(result.canonical, [CONTRACT_TYPE_CDI])
        self.assertEqual(result.unknown, ["Contrat spécial"])

    def test_normalize_contract_type_returns_first_canonical_value(self):
        self.assertEqual(normalize_contract_type("CDD - CDI"), CONTRACT_TYPE_CDD)
        self.assertIsNone(normalize_contract_type("   "))

    def test_normalize_contract_types_is_safe_for_malformed_values(self):
        self.assertEqual(normalize_contract_types(None), [])
        self.assertEqual(normalize_contract_types(["CDI", None, 42]), [CONTRACT_TYPE_CDI])
        self.assertEqual(
            normalize_contract_types(["CDI - CDD", ["Stage", "Freelance"]]),
            [
                CONTRACT_TYPE_CDI,
                CONTRACT_TYPE_CDD,
                CONTRACT_TYPE_INTERNSHIP,
                CONTRACT_TYPE_FREELANCE,
            ],
        )

    def test_normalize_contract_types_supports_arabic_aliases(self):
        self.assertEqual(normalize_contract_types("تربص"), [CONTRACT_TYPE_INTERNSHIP])
        self.assertEqual(normalize_contract_types("عمل حر"), [CONTRACT_TYPE_FREELANCE])

    def test_normalize_work_mode(self):
        self.assertEqual(normalize_work_mode("Oui"), WORK_MODE_REMOTE)
        self.assertEqual(normalize_work_mode("remote"), WORK_MODE_REMOTE)
        self.assertEqual(normalize_work_mode("télétravail"), WORK_MODE_REMOTE)
        self.assertEqual(normalize_work_mode("Hybride"), WORK_MODE_HYBRID)
        self.assertEqual(normalize_work_mode("Non"), WORK_MODE_ON_SITE)
        self.assertEqual(normalize_work_mode("عمل عن بعد"), WORK_MODE_REMOTE)
        self.assertEqual(normalize_work_mode("unknown"), WORK_MODE_UNSPECIFIED)

    def test_normalize_schedule(self):
        self.assertEqual(normalize_schedule("Plein temps"), SCHEDULE_FULL_TIME)
        self.assertEqual(normalize_schedule("Temps plein"), SCHEDULE_FULL_TIME)
        self.assertEqual(normalize_schedule("full-time"), SCHEDULE_FULL_TIME)
        self.assertEqual(normalize_schedule("Mi-temps/Temps partiel"), SCHEDULE_PART_TIME)
        self.assertEqual(normalize_schedule("part time"), SCHEDULE_PART_TIME)
        self.assertEqual(normalize_schedule("دوام كامل"), SCHEDULE_FULL_TIME)
        self.assertEqual(normalize_schedule(None), SCHEDULE_UNSPECIFIED)
