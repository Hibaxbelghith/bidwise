from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol

from ai.llm.providers import LLMProviderError, LLMProviderUnavailable, get_llm_provider


logger = logging.getLogger(__name__)

LLM_MODERATION_PROVIDER = "gemini"

CATEGORY_LEGITIMATE = "legitimate_opportunity"
CATEGORY_SCAM = "scam"
CATEGORY_MLM = "mlm_or_pyramid"
CATEGORY_ADVERTISEMENT = "advertisement"
CATEGORY_INAPPROPRIATE = "inappropriate_content"
CATEGORY_IRRELEVANT = "irrelevant"
CATEGORY_UNCLEAR = "unclear"

DECISION_APPROVED = "approved"
DECISION_PENDING_REVIEW = "pending_review"
DECISION_NEEDS_CHANGES = "needs_changes"
DECISION_REJECTED = "rejected"

ALLOWED_CATEGORIES = frozenset(
    {
        CATEGORY_LEGITIMATE,
        CATEGORY_SCAM,
        CATEGORY_MLM,
        CATEGORY_ADVERTISEMENT,
        CATEGORY_INAPPROPRIATE,
        CATEGORY_IRRELEVANT,
        CATEGORY_UNCLEAR,
    }
)
ALLOWED_DECISIONS = frozenset(
    {
        DECISION_APPROVED,
        DECISION_PENDING_REVIEW,
        DECISION_NEEDS_CHANGES,
        DECISION_REJECTED,
    }
)

LLM_MODERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": sorted(ALLOWED_CATEGORIES),
        },
        "decision": {
            "type": "string",
            "enum": sorted(ALLOWED_DECISIONS),
        },
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["category", "decision", "confidence", "reason"],
}


class JsonProvider(Protocol):
    provider_name: str
    model: str

    def generate_json(self, prompt: str, *, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        ...


@dataclass
class ModerationLLMResult:
    category: str
    decision: str
    confidence: float
    reason: str
    provider: str = LLM_MODERATION_PROVIDER
    model: str = ""
    skipped: bool = False
    raw_decision: str = ""
    raw_category: str = ""
    error: str = ""

    @property
    def final_decision(self) -> str:
        return self.decision

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "skipped": self.skipped,
            "provider": self.provider,
            "model": self.model,
            "category": self.category,
            "decision": self.decision,
            "confidence": round(float(self.confidence), 3),
            "reason": self.reason,
            "final_decision": self.decision,
        }
        if self.raw_category and self.raw_category != self.category:
            payload["raw_category"] = self.raw_category
        if self.raw_decision and self.raw_decision != self.decision:
            payload["raw_decision"] = self.raw_decision
        if self.error:
            payload["error"] = self.error
        return payload


def failed_llm_result(reason: str, *, error: str = "") -> ModerationLLMResult:
    return ModerationLLMResult(
        skipped=True,
        category=CATEGORY_UNCLEAR,
        decision=DECISION_PENDING_REVIEW,
        confidence=0.0,
        reason=_safe_text(reason, limit=200) or "LLM moderation unavailable; kept for admin review.",
        error=_safe_text(error, limit=200),
    )


def _safe_text(value: Any, *, limit: int = 1200) -> str:
    text = str(value or "").strip()
    return text[:limit]


def _safe_list(value: Any, *, limit: int = 20) -> list[Any]:
    if not isinstance(value, list):
        return []
    return value[:limit]


def _drop_document_urls(project_details: dict[str, Any]) -> dict[str, Any]:
    details = dict(project_details)
    documents = details.get("documents")
    if isinstance(documents, list):
        details["documents"] = [
            {
                "type": doc.get("type"),
                "label": doc.get("label"),
                "filename": doc.get("filename"),
            }
            for doc in documents
            if isinstance(doc, dict)
        ][:5]
    return details


def _compact_type_details(payload: dict[str, Any]) -> dict[str, Any]:
    project_details = payload.get("project_details") if isinstance(payload.get("project_details"), dict) else {}
    internship_details = payload.get("internship_details") if isinstance(payload.get("internship_details"), dict) else {}
    seasonal_details = payload.get("seasonal_details") if isinstance(payload.get("seasonal_details"), dict) else {}

    details: dict[str, Any] = {}
    if project_details:
        details["project_details"] = _drop_document_urls(project_details)
    if internship_details:
        details["internship_details"] = internship_details
    if seasonal_details:
        details["seasonal_details"] = seasonal_details
    return details


def compact_moderation_payload(
    payload: dict[str, Any],
    *,
    org_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = org_profile
    compact = {
        "opportunity_type": payload.get("type") or payload.get("opportunity_type"),
        "title": payload.get("title") or payload.get("titre"),
        "description": _safe_text(payload.get("description"), limit=2200),
        "contract": payload.get("contract"),
        "availability": payload.get("availability"),
        "location": payload.get("location") or payload.get("ville"),
        "deadline": payload.get("deadline"),
        "salary": payload.get("salary"),
        "salary_min": payload.get("salary_min"),
        "salary_max": payload.get("salary_max"),
        "experience_min": payload.get("experience_min"),
        "experience_max": payload.get("experience_max"),
        "skills": _safe_list(payload.get("skills"), limit=30),
    }
    compact.update(_compact_type_details(payload))
    return compact


def _build_prompt(payload: dict[str, Any], *, org_profile: dict[str, Any] | None = None) -> str:
    context = compact_moderation_payload(payload, org_profile=org_profile)
    return (
        "You are a moderation classifier for BidWise, a professional platform\n"
        "in Tunisia for job offers, internships, seasonal jobs, and public\n"
        "tenders (appels d'offres / مناقصات عمومية).\n\n"
        "Your sole task: read the opportunity and decide if it is safe to\n"
        "publish without human review.\n"
        "You are replacing a human moderator who asks:\n"
        "\"Is this a real professional opportunity, or is something wrong here?\"\n\n"
        "────────────────────────────────────────────────────────────────\n"
        "WHAT YOU DO NOT DO\n"
        "────────────────────────────────────────────────────────────────\n"
        "Salary ranges, dates, required fields, and type validation are\n"
        "already enforced by the platform before you are called.\n"
        "Do not revalidate them.\n\n"
        "────────────────────────────────────────────────────────────────\n"
        "LANGUAGE\n"
        "────────────────────────────────────────────────────────────────\n"
        "Offers may be in Arabic, French, English, or any mix.\n"
        "Judge intent and meaning, never language or writing style.\n"
        "The reason field must always be written in clear English for the admin dashboard.\n\n"
        "────────────────────────────────────────────────────────────────\n"
        "WHAT IS NOT A PROBLEM — NEVER FLAG THESE\n"
        "────────────────────────────────────────────────────────────────\n"
        "- Informal or casual writing tone\n"
        "- Short description if professional intent is clear\n"
        "- Missing optional fields\n"
        "- Typos, dialect, or regional expressions\n"
        "- Arabic dialect or code-switching (Arabic/French/English mix)\n"
        "- Salary, compensation, or indemnity mentioned\n"
        "  (money going TO the candidate is normal)\n"
        "- Cautionnement provisoire, budget, or financial scope\n"
        "  in a public tender (standard procurement amounts)\n"
        "- Any amount committed by the BUYER in a tender document\n\n"
        "────────────────────────────────────────────────────────────────\n"
        "FINANCIAL SIGNAL — CRITICAL DISTINCTION\n"
        "────────────────────────────────────────────────────────────────\n"
        "The only financial red flag is the DIRECTION of payment:\n\n"
        "  Organization → Candidate = normal (salary, indemnity, compensation)\n"
        "  Buyer → Market = normal (tender budget, cautionnement)\n"
        "  Candidate → Organization = ALWAYS scam, no exceptions\n\n"
        "In public tenders, these are legitimate and must never be flagged:\n"
        "  - Cautionnement provisoire / caution (bid bond paid by bidder\n"
        "    as standard guarantee, NOT a scam)\n"
        "  - Montant estimatif, budget prévisionnel\n"
        "  - Garantie de bonne exécution\n\n"
        "The ONLY scam signal: the candidate or applicant is explicitly\n"
        "asked to send money to the organization or a third party as a\n"
        "condition to apply, start working, or receive anything.\n\n"
        "────────────────────────────────────────────────────────────────\n"
        "CATEGORIES\n"
        "────────────────────────────────────────────────────────────────\n\n"
        "legitimate_opportunity\n"
        "  A real offer from a real employer or contracting authority.\n"
        "  Professional intent is evident.\n"
        "  Approve it. Do not look for reasons to block it.\n\n"
        "scam\n"
        "  At least one hard signal present:\n"
        "  · Candidate asked to pay anything before or after hiring\n"
        "    (frais de dossier, frais d'inscription, recharge, dépôt,\n"
        "     kit de démarrage, crypto, Western Union, virement,\n"
        "     رسوم تسجيل, رسوم على المتقدم, ادفع للتقديم)\n"
        "  · Guaranteed unrealistic income\n"
        "    (\"earn 800 TND/day from home, no experience needed\",\n"
        "     \"دخل يومي مضمون بدون خبرة\")\n"
        "  · Contact restricted to WhatsApp/Telegram/Signal only,\n"
        "    with no company name, address, or official channel anywhere\n"
        "  · Link or instruction designed to harvest personal data\n"
        "    outside the platform\n\n"
        "mlm_or_pyramid\n"
        "  No real employer, no real role, no real product or service.\n"
        "  Income depends entirely on recruiting others into the scheme.\n\n"
        "advertisement\n"
        "  Content promotes a product, service, software, or brand.\n"
        "  There is no actual hiring or procurement intent.\n\n"
        "inappropriate_content\n"
        "  Hate speech, slurs, explicit sexual content, discriminatory\n"
        "  hiring conditions, threats, or content violating Tunisian law.\n\n"
        "irrelevant\n"
        "  Random text, test input, lorem ipsum, or content completely\n"
        "  unrelated to employment or procurement.\n\n"
        "unclear\n"
        "  You have read it carefully and cannot confidently assign\n"
        "  any category above. Something feels off but you cannot\n"
        "  name one specific articulable reason.\n\n"
        "────────────────────────────────────────────────────────────────\n"
        "FEW-SHOT EXAMPLES\n"
        "────────────────────────────────────────────────────────────────\n"
        "Input:\n"
        "{\"opportunity_type\":\"EMPLOI\",\"title\":\"Python Backend Developer\",\"description\":\"We are hiring a backend developer in Tunis to build REST APIs with Django and PostgreSQL. Salary paid monthly by the company.\",\"contract\":\"CDI\",\"salary\":\"1800-2500 TND\",\"experience_min\":2,\"experience_max\":5,\"skills\":[\"Python\",\"Django\",\"SQL\"]}\n"
        "Output:\n"
        "{\"category\":\"legitimate_opportunity\",\"decision\":\"approved\",\"confidence\":0.94,\"reason\":\"The offer describes a real backend developer job with normal salary paid to the candidate.\"}\n\n"
        "Input:\n"
        "{\"opportunity_type\":\"STAGE\",\"title\":\"Stage PFE Data Analyst\",\"description\":\"Nous proposons un stage PFE en analyse de données avec Python, SQL et Power BI au sein de notre équipe data.\",\"contract\":\"Internship\",\"experience_min\":0,\"skills\":[\"Python\",\"SQL\",\"Power BI\"],\"internship_details\":{\"internship_type\":\"graduation_internship\",\"duration_months\":6}}\n"
        "Output:\n"
        "{\"category\":\"legitimate_opportunity\",\"decision\":\"approved\",\"confidence\":0.92,\"reason\":\"The offer clearly describes a real data analysis internship.\"}\n\n"
        "Input:\n"
        "{\"opportunity_type\":\"SAISONNIER\",\"title\":\"Seasonal Customer Support Agent\",\"description\":\"Seasonal support agents needed for summer operations. Candidates will answer customer requests and coordinate with logistics teams.\",\"contract\":\"Seasonal\",\"salary\":\"900 TND\",\"skills\":[\"Communication\",\"Customer support\"],\"seasonal_details\":{\"start_date\":\"2026-07-01\",\"end_date\":\"2026-09-15\"}}\n"
        "Output:\n"
        "{\"category\":\"legitimate_opportunity\",\"decision\":\"approved\",\"confidence\":0.9,\"reason\":\"The content describes a real seasonal customer support position.\"}\n\n"
        "Input:\n"
        "{\"opportunity_type\":\"PROJET\",\"title\":\"Acquisition d'une mini chargeuse\",\"description\":\"Appel d'offres ouvert pour l'acquisition d'une mini chargeuse. Cautionnement provisoire: 1000 TND. Validité des offres: 120 jours.\",\"project_details\":{\"public_buyer\":\"Société d'Exploitation du Canal et Adduction des Eaux du Nord\",\"procedure\":\"Appel d'offres ouvert\",\"number_of_lots\":1,\"documents\":[{\"type\":\"specifications\",\"label\":\"Cahier des charges\",\"filename\":\"cahier-des-charges.pdf\"}]}}\n"
        "Output:\n"
        "{\"category\":\"legitimate_opportunity\",\"decision\":\"approved\",\"confidence\":0.93,\"reason\":\"The offer is a coherent public tender and the bid bond is standard procurement information.\"}\n\n"
        "Input:\n"
        "{\"opportunity_type\":\"EMPLOI\",\"title\":\"Assistant online\",\"description\":\"Travail facile depuis la maison. Envoyez 30 TND frais de dossier par recharge téléphonique pour recevoir le kit de démarrage.\",\"contract\":\"Full time\",\"salary\":\"1500 TND\",\"skills\":[]}\n"
        "Output:\n"
        "{\"category\":\"scam\",\"decision\":\"rejected\",\"confidence\":1.0,\"reason\":\"The candidate is asked to pay fees before starting, which is a scam signal.\"}\n\n"
        "Input:\n"
        "{\"opportunity_type\":\"EMPLOI\",\"title\":\"عمل من المنزل دخل يومي مضمون\",\"description\":\"اربح 500 دينار يومياً بدون خبرة. ادفع 30 دينار رسوم تسجيل للبدء. تواصل واتساب فقط.\"}\n"
        "Output:\n"
        "{\"category\":\"scam\",\"decision\":\"rejected\",\"confidence\":1.0,\"reason\":\"Explicit payment request from candidate (رسوم تسجيل) with unrealistic income guarantee and WhatsApp-only contact.\"}\n\n"
        "Input:\n"
        "{\"opportunity_type\":\"EMPLOI\",\"title\":\"Comptable Tunis\",\"description\":\"Cherchons comptable sérieux. Les candidats d'une certaine origine s'abstenir de postuler.\"}\n"
        "Output:\n"
        "{\"category\":\"inappropriate_content\",\"decision\":\"rejected\",\"confidence\":1.0,\"reason\":\"Discriminatory hiring condition targeting candidates by origin.\"}\n\n"
        "Input:\n"
        "{\"opportunity_type\":\"EMPLOI\",\"title\":\"Business Partner\",\"description\":\"Soyez votre propre patron, développez votre réseau et recrutez d'autres membres pour générer des revenus passifs illimités.\",\"contract\":\"Freelance\",\"skills\":[\"Sales\"]}\n"
        "Output:\n"
        "{\"category\":\"mlm_or_pyramid\",\"decision\":\"pending_review\",\"confidence\":0.86,\"reason\":\"The income appears to depend on recruiting other members rather than a clear professional role.\"}\n\n"
        "Input:\n"
        "{\"opportunity_type\":\"EMPLOI\",\"title\":\"Boost your recruitment\",\"description\":\"Notre logiciel RH vous aide à publier vos annonces plus vite. Contactez notre équipe commerciale pour une démonstration.\",\"contract\":\"\",\"skills\":[]}\n"
        "Output:\n"
        "{\"category\":\"advertisement\",\"decision\":\"rejected\",\"confidence\":0.91,\"reason\":\"The content promotes HR software and does not offer a real opportunity.\"}\n\n"
        "Input:\n"
        "{\"opportunity_type\":\"EMPLOI\",\"title\":\"Test\",\"description\":\"Lorem ipsum test test aaa bbb ccc.\",\"contract\":\"CDI\",\"skills\":[]}\n"
        "Output:\n"
        "{\"category\":\"irrelevant\",\"decision\":\"rejected\",\"confidence\":0.9,\"reason\":\"The content is test text and does not describe an employment or procurement opportunity.\"}\n\n"
        "────────────────────────────────────────────────────────────────\n"
        "DECISION MAPPING\n"
        "────────────────────────────────────────────────────────────────\n"
        "  legitimate_opportunity  + confidence >= 0.82  →  approved\n"
        "  legitimate_opportunity  + confidence <  0.82  →  pending_review\n"
        "  scam                    + confidence >= 0.88  →  rejected\n"
        "  scam                    + confidence <  0.88  →  pending_review\n"
        "  mlm_or_pyramid                                →  pending_review\n"
        "  advertisement                                 →  rejected\n"
        "  inappropriate_content                         →  rejected\n"
        "  irrelevant                                    →  rejected\n"
        "  unclear                                       →  pending_review\n\n"
        "When in doubt between two decisions, always prefer the less severe.\n"
        "approved > pending_review > rejected.\n"
        "Never reject unless you have one specific, articulable hard signal.\n\n"
        "────────────────────────────────────────────────────────────────\n"
        "HARD RULES — NON-NEGOTIABLE\n"
        "────────────────────────────────────────────────────────────────\n"
        "1. Any payment request targeting the candidate →\n"
        "   category: scam, decision: rejected, confidence: 1.0\n"
        "   No context, no framing, no exception changes this.\n\n"
        "2. Most offers on BidWise are legitimate.\n"
        "   Your job is to catch the bad ones, not gatekeep the good ones.\n\n"
        "────────────────────────────────────────────────────────────────\n"
        "REASONING\n"
        "────────────────────────────────────────────────────────────────\n"
        "Analyze the offer carefully before deciding.\n"
        "Think step-by-step internally, then return only the JSON.\n"
        "Base your decision ONLY on the data provided.\n"
        "Do not infer information not present in the payload.\n"
        "If the data is insufficient to decide, return pending_review.\n\n"
        "────────────────────────────────────────────────────────────────\n"
        "OUTPUT — STRICT JSON ONLY\n"
        "────────────────────────────────────────────────────────────────\n"
        "Return ONLY the JSON object.\n"
        "Any text outside the JSON will cause a system error.\n\n"
        "{\n"
        "  \"category\": \"legitimate_opportunity | scam | mlm_or_pyramid | advertisement | inappropriate_content | irrelevant | unclear\",\n"
        "  \"decision\": \"approved | pending_review | needs_changes | rejected\",\n"
        "  \"confidence\": <float 0.00–1.00>,\n"
        "  \"reason\": \"<one clear English sentence for the admin dashboard>\"\n"
        "}\n\n"
        f"Opportunity JSON:\n{json.dumps(context, ensure_ascii=False, sort_keys=True)}"
    )


def _normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _normalize_category(value: Any) -> tuple[str, str]:
    raw = str(value or "").strip().lower()
    return (raw if raw in ALLOWED_CATEGORIES else CATEGORY_UNCLEAR, raw)


def _normalize_decision(value: Any) -> tuple[str, str]:
    raw = str(value or "").strip().lower()
    return (raw if raw in ALLOWED_DECISIONS else DECISION_PENDING_REVIEW, raw)


def _mapped_decision(category: str, confidence: float, raw_decision: str) -> str:
    if category == CATEGORY_LEGITIMATE:
        return DECISION_APPROVED if confidence >= 0.82 else DECISION_PENDING_REVIEW
    if category == CATEGORY_SCAM:
        return DECISION_REJECTED if confidence >= 0.88 else DECISION_PENDING_REVIEW
    if category == CATEGORY_MLM:
        return DECISION_PENDING_REVIEW
    if category in {CATEGORY_ADVERTISEMENT, CATEGORY_INAPPROPRIATE, CATEGORY_IRRELEVANT}:
        return DECISION_REJECTED
    if raw_decision == DECISION_NEEDS_CHANGES:
        return DECISION_PENDING_REVIEW
    return DECISION_PENDING_REVIEW


def classify_opportunity_with_gemini(
    payload: dict[str, Any],
    *,
    org_profile: dict[str, Any] | None = None,
    provider: JsonProvider | None = None,
) -> ModerationLLMResult:
    try:
        llm_provider = provider or get_llm_provider()
    except LLMProviderUnavailable as exc:
        return failed_llm_result(
            "LLM moderation unavailable; kept for admin review.",
            error=str(exc),
        )

    try:
        raw = llm_provider.generate_json(
            _build_prompt(payload, org_profile=org_profile),
            schema=LLM_MODERATION_SCHEMA,
        )
    except (LLMProviderError, LLMProviderUnavailable) as exc:
        logger.warning("LLM moderation failed: %s", exc)
        return failed_llm_result(
            "LLM moderation failed; kept for admin review.",
            error=str(exc),
        )

    category, raw_category = _normalize_category(raw.get("category"))
    _raw_normalized_decision, raw_decision = _normalize_decision(raw.get("decision"))
    confidence = _normalize_confidence(raw.get("confidence"))
    reason = _safe_text(raw.get("reason"), limit=200) or "LLM returned no moderation reason."
    decision = _mapped_decision(category, confidence, raw_decision)

    logger.info(
        "LLM moderation decision provider=%s model=%s opportunity_type=%s category=%s "
        "raw_decision=%s decision=%s confidence=%.3f",
        getattr(llm_provider, "provider_name", LLM_MODERATION_PROVIDER),
        getattr(llm_provider, "model", ""),
        payload.get("type") or payload.get("opportunity_type") or "",
        category,
        raw_decision,
        decision,
        confidence,
    )

    return ModerationLLMResult(
        skipped=False,
        provider=getattr(llm_provider, "provider_name", LLM_MODERATION_PROVIDER),
        model=getattr(llm_provider, "model", ""),
        category=category,
        decision=decision,
        confidence=confidence,
        reason=reason,
        raw_category=raw_category,
        raw_decision=raw_decision,
    )
