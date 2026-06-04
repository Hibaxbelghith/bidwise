from django.test import SimpleTestCase

from ai.resume_match.evidence import _contract_alignment


class ResumeMatchEvidenceTests(SimpleTestCase):
    def test_contract_alignment_uses_shared_contract_normalization(self):
        self.assertEqual(
            _contract_alignment(
                {"employment_types": ["CDD"]},
                {"contract": "Contract"},
            )["level"],
            "aligned",
        )
        self.assertEqual(
            _contract_alignment(
                {"employment_types": ["CDI"]},
                {"contract": "Permanent contract"},
            )["level"],
            "aligned",
        )

    def test_contract_alignment_reviews_normalized_mismatch(self):
        result = _contract_alignment(
            {"employment_types": ["CDI"]},
            {"contract": "Internship"},
        )

        self.assertEqual(result["level"], "review")
