from __future__ import annotations

import logging
import re
from dataclasses import replace
from typing import Any

from django.conf import settings

from ai.llm.providers import (
    FallbackLLMProvider,
    LLMProvider,
    LLMProviderError,
    LLMProviderUnavailable,
    LLMTransientProviderError,
    OllamaProvider,
    get_llm_provider,
)


logger = logging.getLogger(__name__)


SUPPORTED_TYPES = {"EMPLOI", "STAGE"}
MAX_DESCRIPTION_LENGTH = 3500

DESCRIPTION_DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": "Generated job or internship description in Markdown.",
        },
    },
    "required": ["description"],
    "additionalProperties": False,
}


class DescriptionDraftError(RuntimeError):
    pass


class DescriptionDraftValidationError(DescriptionDraftError):
    def __init__(self, fields: dict[str, list[str]]):
        super().__init__("Invalid description draft input.")
        self.fields = fields


def generate_organization_description_draft(
    values: dict[str, Any],
    *,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    cleaned = _clean_input(values)
    llm_provider = _with_min_output_budget(_get_description_draft_provider(provider), min_tokens=1200)
    prompt = build_description_prompt(**cleaned)

    try:
        payload = llm_provider.generate_json(prompt, schema=DESCRIPTION_DRAFT_SCHEMA)
    except (LLMProviderUnavailable, LLMTransientProviderError, LLMProviderError) as exc:
        logger.warning(
            "Organization description draft failed provider=%s reason=%s",
            getattr(llm_provider, "provider_name", ""),
            exc,
        )
        return _build_deterministic_description(cleaned)

    description = _normalize_description(payload.get("description"))
    if not description:
        raise DescriptionDraftError("The AI provider returned an empty description.")

    return {
        "description": description,
        "provider": getattr(llm_provider, "provider_name", ""),
        "model": getattr(llm_provider, "model", ""),
        "generated": True,
    }


def _build_deterministic_description(values: dict[str, Any]) -> dict[str, Any]:
    title = values["title"]
    skills = values.get("skills") or []
    location = values.get("location") or ""
    contract = values.get("contract") or ""
    work_mode = values.get("work_mode") or ""
    education = values.get("education_level") or ""
    min_experience = values.get("min_experience")
    max_experience = values.get("max_experience")
    is_french = _looks_french(title)

    if is_french:
        context = ", ".join(item for item in (contract, work_mode, location) if item)
        context_sentence = (
            f"Le poste s'inscrit dans un environnement {context}."
            if context
            else "Le poste s'inscrit dans un environnement professionnel collaboratif."
        )
        skill_text = ", ".join(skills[:6]) if skills else "les competences liees au poste"
        experience_text = _french_experience_text(min_experience, max_experience)
        education_text = f" Une formation de niveau {education} est attendue." if education else ""
        responsibilities = _responsibility_lines(skills, language="fr")
        description = (
            f"**A propos du poste**\n"
            f"Nous recherchons un(e) {title} pour contribuer activement aux projets de l'equipe. "
            f"{context_sentence} Cette opportunite permet de developper des competences concretes et de participer a des missions utiles.\n\n"
            f"**Responsabilites**\n"
            + "\n".join(f"- {item}" for item in responsibilities)
            + "\n\n"
            f"**Profil recherche**\n"
            f"Le/la candidat(e) dispose de bases solides en {skill_text}.{education_text}{experience_text} "
            "Rigueur, autonomie, communication et esprit d'equipe sont essentiels pour reussir dans cette fonction.\n\n"
            f"Ce poste est fait pour vous ! Rejoignez-nous pour progresser et contribuer a des projets professionnels concrets."
        )
    else:
        context = ", ".join(item for item in (contract, work_mode, location) if item)
        context_sentence = (
            f"The role is based in a {context} environment."
            if context
            else "The role is part of a collaborative professional environment."
        )
        skill_text = ", ".join(skills[:6]) if skills else "the skills relevant to the role"
        experience_text = _english_experience_text(min_experience, max_experience)
        education_text = f" A {education} education level is expected." if education else ""
        responsibilities = _responsibility_lines(skills, language="en")
        description = (
            f"**About the role**\n"
            f"We are looking for a {title} to contribute actively to the team's projects. "
            f"{context_sentence} This opportunity offers hands-on responsibilities and room for professional development.\n\n"
            f"**Responsibilities**\n"
            + "\n".join(f"- {item}" for item in responsibilities)
            + "\n\n"
            f"**Candidate profile**\n"
            f"The ideal candidate has a solid foundation in {skill_text}.{education_text}{experience_text} "
            "Attention to detail, autonomy, communication, and teamwork are important for success in this role.\n\n"
            "This role is for you. Join us to grow your skills and contribute to meaningful professional projects."
        )

    return {
        "description": _normalize_description(description),
        "provider": "deterministic",
        "model": "",
        "generated": False,
    }


def _looks_french(value: str) -> bool:
    normalized = f" {str(value or '').casefold()} "
    markers = (" developpeur ", " assistant ", " comptable ", " charge ", " responsable ", " stage ")
    return any(marker in normalized for marker in markers) or bool(
        re.search(r"[àâçéèêëîïôùûüÿœ]", normalized)
    )


def _responsibility_lines(skills: list[str], *, language: str) -> list[str]:
    selected = [skill for skill in skills[:4] if skill]
    if language == "fr":
        lines = [
            f"Mettre en oeuvre {skill} dans les missions quotidiennes."
            for skill in selected
        ]
        lines.extend(
            [
                "Collaborer avec les membres de l'equipe sur les priorites du poste.",
                "Documenter les travaux realises et partager les informations utiles.",
                "Contribuer a l'amelioration continue des methodes de travail.",
            ]
        )
    else:
        lines = [
            f"Apply {skill} in day-to-day responsibilities."
            for skill in selected
        ]
        lines.extend(
            [
                "Collaborate with team members on role priorities.",
                "Document completed work and share relevant information.",
                "Contribute to the continuous improvement of working practices.",
            ]
        )
    return lines[:7]


def _french_experience_text(minimum: int | None, maximum: int | None) -> str:
    if minimum is not None and maximum is not None:
        return f" Une experience de {minimum} a {maximum} ans est recherchee."
    if minimum is not None:
        return f" Une experience minimale de {minimum} ans est recherchee."
    return ""


def _english_experience_text(minimum: int | None, maximum: int | None) -> str:
    if minimum is not None and maximum is not None:
        return f" The expected experience range is {minimum} to {maximum} years."
    if minimum is not None:
        return f" At least {minimum} years of experience is expected."
    return ""


def _get_description_draft_provider(provider: LLMProvider | None = None) -> LLMProvider:
    if provider is not None:
        return provider

    primary_provider = get_llm_provider()
    if not bool(getattr(settings, "ORGANIZATION_DESCRIPTION_DRAFT_OLLAMA_FALLBACK_ENABLED", True)):
        return primary_provider

    ollama_provider = _build_ollama_fallback_provider()
    if ollama_provider is None:
        return primary_provider

    if getattr(primary_provider, "provider_name", "") == "ollama":
        return primary_provider

    if hasattr(primary_provider, "providers"):
        providers = tuple(getattr(primary_provider, "providers", ()))
        if any(getattr(item, "provider_name", "") == "ollama" for item in providers):
            return primary_provider
        try:
            return replace(primary_provider, providers=providers + (ollama_provider,))
        except TypeError:
            return primary_provider

    return FallbackLLMProvider(
        providers=(primary_provider, ollama_provider),
        max_retries=int(getattr(settings, "LLM_PROVIDER_MAX_RETRIES", 1)),
        retry_delay_seconds=float(getattr(settings, "LLM_PROVIDER_RETRY_DELAY_SECONDS", 5.0)),
        retry_backoff_factor=float(getattr(settings, "LLM_PROVIDER_RETRY_BACKOFF_FACTOR", 2.0)),
    )


def _build_ollama_fallback_provider() -> LLMProvider | None:
    model = str(getattr(settings, "OLLAMA_MODEL", "") or "").strip()
    if not model:
        return None

    return OllamaProvider(
        model=model,
        base_url=str(getattr(settings, "OLLAMA_BASE_URL", "") or "http://host.docker.internal:11434").rstrip("/"),
        timeout_seconds=float(getattr(settings, "OLLAMA_TIMEOUT_SECONDS", 45.0)),
        temperature=float(getattr(settings, "OLLAMA_TEMPERATURE", 0.0)),
        max_output_tokens=max(int(getattr(settings, "OLLAMA_MAX_OUTPUT_TOKENS", 1200)), 1200),
        keep_alive=str(getattr(settings, "OLLAMA_KEEP_ALIVE", "") or "").strip(),
    )


def _with_min_output_budget(llm_provider: LLMProvider, *, min_tokens: int) -> LLMProvider:
    if hasattr(llm_provider, "providers"):
        providers = tuple(
            _with_min_output_budget(provider, min_tokens=min_tokens)
            for provider in getattr(llm_provider, "providers", ())
        )
        try:
            return replace(llm_provider, providers=providers)
        except TypeError:
            return llm_provider

    current_tokens = getattr(llm_provider, "max_output_tokens", None)
    if current_tokens is None:
        return llm_provider

    try:
        next_tokens = max(int(current_tokens), int(min_tokens))
    except (TypeError, ValueError):
        next_tokens = int(min_tokens)

    if next_tokens == current_tokens:
        return llm_provider

    try:
        return replace(llm_provider, max_output_tokens=next_tokens)
    except TypeError:
        return llm_provider


def _clean_input(values: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(values, dict):
        raise DescriptionDraftValidationError({"detail": ["Payload must be an object."]})

    type_offre = str(values.get("type") or "").strip().upper()
    title = _clean_text(values.get("title"), limit=140)
    errors: dict[str, list[str]] = {}

    if type_offre not in SUPPORTED_TYPES:
        errors["type"] = ["Description drafts are available only for jobs and internships."]
    if len(title) < 5:
        errors["title"] = ["Enter a clear title with at least 5 characters before generating a draft."]
    if errors:
        raise DescriptionDraftValidationError(errors)

    return {
        "type_offre": type_offre,
        "title": title,
        "contract": _clean_text(values.get("contract"), limit=80),
        "work_mode": _clean_text(values.get("work_mode") or values.get("availability"), limit=80),
        "location": _clean_text(values.get("location"), limit=80),
        "skills": _clean_skills(values.get("skills")),
        "min_experience": _clean_number(values.get("min_experience") or values.get("experience_min")),
        "max_experience": _clean_number(values.get("max_experience") or values.get("experience_max")),
        "education_level": _clean_text(values.get("education_level"), limit=100),
        "salary": _clean_text(values.get("salary"), limit=100),
        "deadline": _clean_text(values.get("deadline"), limit=40),
    }


def _clean_text(value: Any, *, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _clean_skills(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_items = value.split(",")
    elif isinstance(value, list):
        raw_items = value
    else:
        raw_items = []
    cleaned = []
    seen = set()
    for item in raw_items:
        skill = _clean_text(item, limit=40)
        key = skill.casefold()
        if skill and key not in seen:
            seen.add(key)
            cleaned.append(skill)
        if len(cleaned) >= 12:
            break
    return cleaned


def _clean_number(value: Any) -> int | None:
    if value in ("", None):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0 or parsed > 60:
        return None
    return parsed


def _normalize_description(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:MAX_DESCRIPTION_LENGTH].strip()


def build_description_prompt(
    type_offre: str,
    title: str,
    contract: str = "",
    work_mode: str = "",
    location: str = "",
    skills: list[str] | None = None,
    min_experience: int | None = None,
    max_experience: int | None = None,
    education_level: str = "",
    salary: str = "",
    deadline: str = "",
) -> str:
    type_label = "emploi" if type_offre == "EMPLOI" else "stage professionnel"

    context_lines = [f"- Intitule : {title}", f"- Type : {type_label}"]
    if contract:
        context_lines.append(f"- Contrat : {contract}")
    if work_mode:
        context_lines.append(f"- Mode de travail : {work_mode}")
    if location:
        context_lines.append(f"- Lieu : {location}")
    if skills:
        skills_str = ", ".join(skill.strip() for skill in skills if skill.strip())
        if skills_str:
            context_lines.append(f"- Competences mentionnees : {skills_str}")
    if min_experience is not None and max_experience is not None:
        context_lines.append(f"- Experience : {min_experience} a {max_experience} ans")
    elif min_experience is not None:
        context_lines.append(f"- Experience minimale : {min_experience} ans")
    if education_level:
        context_lines.append(f"- Niveau d'etudes : {education_level}")
    if salary:
        context_lines.append(f"- Remuneration : {salary}")
    if deadline:
        context_lines.append(f"- Date limite : {deadline}")

    context_block = "\n".join(context_lines)

    return f"""
Tu es un expert RH senior specialise dans la redaction d'offres d'emploi attractives et professionnelles, dans le style des grandes plateformes de recrutement comme Indeed, LinkedIn et Welcome to the Jungle.

## Tache
A partir des informations fournies, redige une description de poste professionnelle, humaine et engageante.
Elle doit donner envie de postuler tout en restant credible et precise.

## Informations du poste
{context_block}

## Regle de langue
- Detecte la langue du titre du poste.
- Francais si titre en francais -> redige tout en francais.
- Anglais si titre en anglais -> redige tout en anglais.
- Ne melange jamais les deux.

## Structure obligatoire - 3 sections dans cet ordre exact

**A propos du poste**
Un seul paragraphe en prose de 3 phrases maximum. Presente le contexte du role, l'environnement de travail et la valeur ajoutee pour le candidat. Ne nomme aucune entreprise.

**Responsabilites**
Liste de 7 points maximum en bullet. Chaque point commence par un verbe d'action a l'infinitif. Les missions doivent etre concretes et specifiques au metier. Si des competences techniques sont mentionnees, integre-les dans des missions realistes. Tu peux mentionner des technologies proches de l'ecosysteme, mais jamais hors sujet.

**Profil recherche**
1 a 2 paragraphes en prose fluide, sans bullet point. Integre la formation attendue, les competences techniques, les qualites humaines et le niveau d'experience si fourni. La derniere phrase doit etre un appel a l'action engageant de ce style : "Ce poste est fait pour vous ! Rejoignez-nous pour [benefice concret lie au poste]."

## Regles de longueur - STRICTES
- A propos du poste : 3 phrases maximum, pas une de plus.
- Responsabilites : 7 points maximum, chaque point maximum 20 mots.
- Profil recherche : 2 paragraphes maximum, 80 mots par paragraphe maximum.
- Longueur totale : 280 a 360 mots. Ne depasse jamais 360 mots.
- Si tu manques de place, reduis chaque bullet, pas le nombre de sections.

## Regles de qualite
- Ton humain et direct, ni trop formel ni trop familier.
- Langage inclusif en francais : utilise "le/la candidat(e)", "etudiant(e)", "curieux(se)".
- Ne nomme jamais une entreprise specifique.
- Ne promets pas un salaire si non fourni ; si necessaire, ecris "remuneration selon profil".
- N'ajoute aucune section supplementaire.
- N'ecris pas "genere par IA" ni aucune mention de l'outil.
- Retourne uniquement le contenu des 3 sections.

## Format JSON obligatoire
Retourne uniquement un objet JSON valide :
{{
  "description": "**A propos du poste**\\n[paragraphe]\\n\\n**Responsabilites**\\n- [point 1]\\n- [point 2]\\n\\n**Profil recherche**\\n[paragraphe(s)]"
}}
""".strip()
