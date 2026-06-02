from __future__ import annotations

from typing import Any


PRIMARY_BUSINESS_FAMILIES = (
    "software_web",
    "data_ai",
    "devops_cloud_infrastructure",
    "it_network_support",
    "accounting_finance_audit",
    "sales_business",
    "marketing_communication",
    "hr_administration",
    "quality_industry_methods",
    "engineering_construction",
    "legal_regulatory",
    "healthcare",
    "education_training",
    "logistics_supply_chain",
    "design_creative",
    "customer_support",
    "security_safety",
    "other",
)

PRIMARY_BUSINESS_FAMILY_DESCRIPTIONS = {
    "software_web": "Software engineering and web/mobile application development.",
    "data_ai": "Data engineering, BI, analytics, big data, machine learning and AI.",
    "devops_cloud_infrastructure": (
        "DevOps, cloud infrastructure, CI/CD, containers, infrastructure automation and monitoring."
    ),
    "it_network_support": "IT support, systems, networks, helpdesk and user technical assistance.",
    "accounting_finance_audit": "Accounting, finance, audit, payroll, tax and financial control.",
    "sales_business": "Sales, commercial development, business development and account management.",
    "marketing_communication": "Marketing, communication, content, social media, SEO and branding.",
    "hr_administration": "Human resources, recruitment, administration, office management and back office.",
    "quality_industry_methods": "Quality, industrial methods, production, maintenance and continuous improvement.",
    "engineering_construction": "Engineering, civil engineering, construction, architecture and technical studies.",
    "legal_regulatory": "Legal, compliance, contracts, regulatory and governance.",
    "healthcare": "Healthcare, medical, paramedical, pharmacy, nursing and patient care.",
    "education_training": "Education, teaching, training and coaching.",
    "logistics_supply_chain": "Logistics, transport, supply chain, procurement, warehouse and inventory.",
    "design_creative": "Design, UX/UI, creative production, visual design and CAD-oriented creative work.",
    "customer_support": "Customer service, client support, call center and after-sales support.",
    "security_safety": "Security, safety, surveillance, HSE, risk prevention and access control.",
    "other": "Use only when no listed family fits the CV.",
}

CONTROLLED_FAMILIES = {
    *PRIMARY_BUSINESS_FAMILIES,
    "backend",
    "frontend",
    "fullstack",
    "accounting_finance",
    "marketing",
    "sales",
    "hr",
    "design",
    "it_support_network",
    "quality_industry",
    "administration",
    "legal",
}

COMPATIBLE_FAMILY_GROUPS = (
    {"software_web", "backend", "frontend", "fullstack", "devops_cloud_infrastructure"},
    {"sales_business", "sales", "marketing"},
    {"marketing_communication", "marketing", "sales"},
    {"devops_cloud_infrastructure", "it_network_support", "it_support_network", "backend"},
    {"accounting_finance_audit", "accounting_finance"},
    {"quality_industry_methods", "quality_industry", "engineering_construction"},
    {"design_creative", "design"},
    {"legal_regulatory", "legal"},
    {"hr_administration", "hr", "administration"},
    {"customer_support", "sales"},
    {"security_safety", "quality_industry_methods", "quality_industry"},
)


def _clean_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, (tuple, set)):
        raw_items = list(value)
    elif value:
        raw_items = [value]
    else:
        raw_items = []
    return [str(item).strip() for item in raw_items if str(item or "").strip()]


def normalize_family(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return text if text in CONTROLLED_FAMILIES else ""


def normalize_family_set(values: Any) -> set[str]:
    return {family for family in (normalize_family(value) for value in _clean_list(values)) if family}


def profile_business_families(features: dict[str, Any] | None) -> set[str]:
    features = features if isinstance(features, dict) else {}
    try:
        family_confidence = float(features.get("profile_family_confidence") or 0.0)
    except (TypeError, ValueError):
        family_confidence = 0.0

    explicit_families = normalize_family_set(
        features.get("profile_business_families") or features.get("business_families")
    ) - {"other"}
    if explicit_families:
        return explicit_families

    semantic_resume_families = normalize_family_set(features.get("semantic_resume_business_families")) - {"other"}
    if semantic_resume_families and family_confidence >= 0.75:
        return semantic_resume_families
    return normalize_family_set(features.get("interests")) - {"other"}


def opportunity_llm_business_families(
    opportunity: Any,
    *,
    min_confidence: float = 0.70,
    min_family_confidence: float = 0.75,
) -> set[str]:
    extra_data = getattr(opportunity, "extra_data", None)
    if isinstance(opportunity, dict):
        extra_data = opportunity.get("extra_data")
    if not isinstance(extra_data, dict):
        return set()
    payload = extra_data.get("llm_enrichment")
    if not isinstance(payload, dict):
        return set()
    try:
        confidence = float(payload.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < min_confidence:
        return set()
    try:
        family_confidence = float(payload.get("family_confidence") or 0.0)
    except (TypeError, ValueError):
        family_confidence = 0.0
    if family_confidence < min_family_confidence:
        return set()
    return normalize_family_set(payload.get("business_families")) - {"other"}


def opportunity_text_business_families(opportunity: Any, *, include_description: bool = True) -> set[str]:
    return set()


def families_are_compatible(profile_families: set[str], opportunity_families: set[str]) -> bool:
    if not profile_families or not opportunity_families:
        return False
    if profile_families.intersection(opportunity_families):
        return True
    for group in COMPATIBLE_FAMILY_GROUPS:
        if profile_families.intersection(group) and opportunity_families.intersection(group):
            return True
    return False
