from __future__ import annotations

import re
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
    "devops_cloud_infrastructure": "DevOps, cloud infrastructure, CI/CD, containers, infrastructure automation and monitoring.",
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
    "software_web",
    "devops_cloud_infrastructure",
    "it_network_support",
    "accounting_finance_audit",
    "sales_business",
    "marketing_communication",
    "hr_administration",
    "quality_industry_methods",
    "legal_regulatory",
    "healthcare",
    "logistics_supply_chain",
    "design_creative",
    "customer_support",
    "security_safety",
    "backend",
    "frontend",
    "fullstack",
    "data_ai",
    "accounting_finance",
    "marketing",
    "sales",
    "hr",
    "design",
    "it_support_network",
    "quality_industry",
    "engineering_construction",
    "administration",
    "education_training",
    "legal",
    "other",
}

COMPATIBLE_FAMILY_GROUPS = (
    {"software_web", "backend", "frontend", "fullstack", "devops_cloud_infrastructure"},
    {"sales_business", "sales", "marketing"},
    {"marketing_communication", "marketing", "sales"},
    {"devops_cloud_infrastructure", "it_network_support", "it_support_network", "backend"},
    {"it_network_support", "it_support_network"},
    {"accounting_finance_audit", "accounting_finance"},
    {"quality_industry_methods", "quality_industry", "engineering_construction"},
    {"design_creative", "design"},
    {"legal_regulatory", "legal"},
    {"hr_administration", "hr", "administration"},
    {"customer_support", "sales"},
    {"security_safety", "quality_industry_methods", "quality_industry"},
)

FAMILY_KEYWORDS = {
    "backend": (
        "backend",
        "back end",
        "api",
        "django",
        "fastapi",
        "flask",
        "python developer",
        "nest",
        "express",
    ),
    "frontend": (
        "frontend",
        "front end",
        "react",
        "vue",
        "angular",
        "typescript",
        "ui developer",
        "web designer",
    ),
    "fullstack": (
        "full stack",
        "fullstack",
        "mern",
        "mean",
        "developpeur web",
        "développeur web",
    ),
    "data_ai": (
        "data",
        "machine learning",
        "ai engineer",
        "ia",
        "nlp",
        "pytorch",
        "tensorflow",
        "power bi",
        "business intelligence",
    ),
    "devops_cloud_infrastructure": (
        "devops",
        "dev ops",
        "cloud",
        "aws",
        "azure",
        "gcp",
        "docker",
        "kubernetes",
        "terraform",
        "infrastructure as code",
        "iac",
        "ci/cd",
        "cicd",
        "github actions",
        "gitlab ci",
        "jenkins",
        "prometheus",
        "grafana",
        "monitoring",
        "logging",
        "deployment",
        "containerization",
        "containerisation",
    ),
    "accounting_finance": (
        "comptable",
        "comptabilite",
        "comptabilité",
        "accounting",
        "finance",
        "sage",
        "payroll",
        "tax",
    ),
    "marketing": (
        "marketing",
        "seo",
        "content",
        "community management",
        "social media",
        "digital marketing",
    ),
    "sales": (
        "sales",
        "commercial",
        "business development",
        "vente",
        "prospection",
    ),
    "hr": (
        "human resources",
        "ressources humaines",
        "rh",
        "talent acquisition",
        "recruitment",
        "recrutement",
    ),
    "design": (
        "design",
        "designer",
        "photoshop",
        "illustrator",
        "figma",
        "autocad",
        "catia",
        "harness",
    ),
    "it_support_network": (
        "support it",
        "support informatique",
        "support utilisateur",
        "support utilisateurs",
        "assistance technique",
        "assistance utilisateurs",
        "technicien support",
        "technicien informatique",
        "maintenance informatique",
        "network",
        "reseau",
        "réseau",
        "system",
        "systeme",
        "système",
        "systemes",
        "systèmes",
        "erp",
        "infrastructure",
        "helpdesk",
        "help desk",
        "ticketing",
        "active directory",
        "windows",
        "tcp/ip",
    ),
    "quality_industry": (
        "quality",
        "qualite",
        "qualité",
        "industry",
        "industrial",
        "industrialisation",
        "cnc",
        "usinage",
        "production",
        "fabrication",
        "atelier",
        "methodes",
        "méthodes",
        "methode",
        "méthode",
        "gamme de fabrication",
        "gammes de fabrication",
        "instruction de travail",
        "instructions de travail",
        "amelioration continue",
        "amélioration continue",
        "maintenance",
        "iso",
    ),
    "engineering_construction": (
        "civil engineering",
        "genie civil",
        "gÃ©nie civil",
        "construction",
        "chantier",
        "ouvrage d'art",
        "ouvrages d'art",
        "structure",
        "structures",
        "hydraulique",
        "hydraulic",
        "bim",
        "revit",
        "autocad",
        "graitec",
        "advance structure",
        "infrastructure",
        "batiment",
        "bÃ¢timent",
        "travaux",
    ),
    "administration": (
        "assistante administrative",
        "assistante administratif",
        "assistant administratif",
        "assistant administrative",
        "adjointe administrative",
        "adjoint administratif",
        "employée administrative",
        "employe administratif",
        "gestion administrative",
        "administratif",
        "administrative",
        "administration",
        "office manager",
        "bureau",
        "archivage",
        "classement",
        "secretariat",
        "secrétariat",
    ),
    "education_training": (
        "trainer",
        "formateur",
        "teacher",
        "education",
        "training",
    ),
    "legal": (
        "legal",
        "juridique",
        "law",
        "avocat",
    ),
    "healthcare": (
        "healthcare",
        "santÃ©",
        "sante",
        "paramÃ©dical",
        "paramedical",
        "bloc opÃ©ratoire",
        "bloc operatoire",
        "instrumentiste",
        "infirmier",
        "infirmiÃ¨re",
        "infirmiere",
        "sage-femme",
        "pharmacie",
        "anesthÃ©sie",
        "anesthesie",
        "rÃ©animation",
        "reanimation",
        "pÃ©diatrie",
        "pediatrie",
        "patient",
        "soins",
        "clinique",
    ),
    "security_safety": (
        "agent de sécurité",
        "agents de sécurité",
        "sécurité des personnes",
        "securite des personnes",
        "sécurité des biens",
        "securite des biens",
        "gardiennage",
        "surveillance",
        "contrôle d'accès",
        "controle d'acces",
        "prévention des risques",
        "prevention des risques",
        "sécurité incendie",
        "securite incendie",
        "sûreté",
        "surete",
        "hse",
        "qhse",
        "qhsse",
    ),
}


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


def families_from_text_values(values: Any) -> set[str]:
    text = " ".join(_clean_list(values)).casefold()
    if not text:
        return set()
    families = set()
    for family, keywords in FAMILY_KEYWORDS.items():
        if any(_contains_keyword_phrase(text, keyword) for keyword in keywords):
            families.add(family)
    return families


def _contains_keyword_phrase(text: str, keyword: str) -> bool:
    normalized_keyword = str(keyword or "").casefold().strip()
    if not normalized_keyword:
        return False
    pattern = r"(?<![\w])" + re.escape(normalized_keyword) + r"(?![\w])"
    return bool(re.search(pattern, text, flags=re.UNICODE))


def profile_business_families(features: dict[str, Any] | None) -> set[str]:
    features = features if isinstance(features, dict) else {}
    try:
        family_confidence = float(features.get("profile_family_confidence") or 0.0)
    except (TypeError, ValueError):
        family_confidence = 0.0
    explicit_families = normalize_family_set(
        features.get("profile_business_families")
        or features.get("semantic_resume_business_families")
        or features.get("business_families")
    ) - {"other"}
    if explicit_families and family_confidence >= 0.75:
        return explicit_families

    values = []
    explicit_interest_families = normalize_family_set(features.get("interests")) - {"other"}
    explicit_values = []
    for key in ("target_roles", "roles", "profile_skills"):
        explicit_values.extend(_clean_list(features.get(key)))
    if explicit_values:
        values.extend(explicit_values)
        values.extend(_clean_list(features.get("interests")))
    else:
        for key in ("skills", "interests"):
            values.extend(_clean_list(features.get(key)))
    return explicit_interest_families | families_from_text_values(values)


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
    families = normalize_family_set(payload.get("business_families"))
    return families - {"other"}


def opportunity_text_business_families(opportunity: Any, *, include_description: bool = True) -> set[str]:
    if isinstance(opportunity, dict):
        values = [
            opportunity.get("titre"),
            opportunity.get("skills"),
        ]
        if include_description:
            values.append(opportunity.get("description"))
    else:
        values = [
            getattr(opportunity, "titre", ""),
            getattr(opportunity, "skills", []),
        ]
        if include_description:
            values.append(getattr(opportunity, "description", ""))
    return families_from_text_values(values)


def families_are_compatible(profile_families: set[str], opportunity_families: set[str]) -> bool:
    if not profile_families or not opportunity_families:
        return False
    if profile_families.intersection(opportunity_families):
        return True
    for group in COMPATIBLE_FAMILY_GROUPS:
        if profile_families.intersection(group) and opportunity_families.intersection(group):
            return True
    return False
