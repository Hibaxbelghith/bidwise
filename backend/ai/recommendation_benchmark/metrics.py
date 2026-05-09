from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from statistics import mean
from typing import Any, Iterable

from .dataset import ExpectedResult


CONFIDENCE_VALUE = {
    "LOW": 0.33,
    "MEDIUM": 0.66,
    "HIGH": 1.0,
}

SEMANTIC_CATEGORY_TERMS = {
    "backend": {"python", "django", "fastapi", "postgresql", "redis", "celery", "rest api", "backend"},
    "frontend": {"react", "typescript", "javascript", "css", "frontend", "web development"},
    "devops": {"docker", "kubernetes", "terraform", "aws", "devops", "github actions", "gitlab ci"},
    "ai": {"machine learning", "natural language processing", "python"},
    "data": {"sql", "apache airflow", "apache spark", "data engineering", "python"},
    "cybersecurity": {"cybersecurity"},
    "hr": {"human resources"},
    "accounting": {"accounting"},
    "nurse": {"nursing"},
    "marketing": {"marketing"},
}


def normalize_title(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    text = re.sub(r"[^\w\s\u0600-\u06ff+-]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def recommendation_title(item: dict[str, Any]) -> str:
    return str(item.get("title") or item.get("titre") or "")


def _top_k(recommendations: Iterable[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    return list(recommendations)[: max(0, int(top_k))]


def _expected_sets(expected: ExpectedResult) -> tuple[set[str], set[str]]:
    return (
        {normalize_title(title) for title in expected.should_match},
        {normalize_title(title) for title in expected.should_not_match},
    )


def _is_relevant(item: dict[str, Any], expected_matches: set[str]) -> bool:
    return normalize_title(recommendation_title(item)) in expected_matches


def _is_explicit_noise(item: dict[str, Any], expected_non_matches: set[str]) -> bool:
    return normalize_title(recommendation_title(item)) in expected_non_matches


def precision_at_k(recommendations: Iterable[dict[str, Any]], expected: ExpectedResult, top_k: int) -> float:
    items = _top_k(recommendations, top_k)
    if not items:
        return 0.0
    should_match, _ = _expected_sets(expected)
    return sum(1 for item in items if _is_relevant(item, should_match)) / len(items)


def recall_at_k(recommendations: Iterable[dict[str, Any]], expected: ExpectedResult, top_k: int) -> float:
    should_match, _ = _expected_sets(expected)
    if not should_match:
        return 0.0
    items = _top_k(recommendations, top_k)
    found = {normalize_title(recommendation_title(item)) for item in items}.intersection(should_match)
    return len(found) / len(should_match)


def noise_rate(recommendations: Iterable[dict[str, Any]], expected: ExpectedResult, top_k: int) -> float:
    items = _top_k(recommendations, top_k)
    if not items:
        return 0.0
    _, should_not_match = _expected_sets(expected)
    return sum(1 for item in items if _is_explicit_noise(item, should_not_match)) / len(items)


def exact_match_rate(recommendations: Iterable[dict[str, Any]], expected: ExpectedResult, top_k: int) -> float:
    return precision_at_k(recommendations, expected, top_k)


def false_positive_rate(recommendations: Iterable[dict[str, Any]], expected: ExpectedResult, top_k: int) -> float:
    items = _top_k(recommendations, top_k)
    if not items:
        return 0.0
    _, should_not_match = _expected_sets(expected)
    false_positives = sum(1 for item in items if _is_explicit_noise(item, should_not_match))
    return false_positives / len(items)


def mean_reciprocal_rank(recommendations: Iterable[dict[str, Any]], expected: ExpectedResult, top_k: int) -> float:
    should_match, _ = _expected_sets(expected)
    for index, item in enumerate(_top_k(recommendations, top_k), start=1):
        if _is_relevant(item, should_match):
            return 1.0 / index
    return 0.0


def average_semantic_score(recommendations: Iterable[dict[str, Any]], expected: ExpectedResult, top_k: int) -> float:
    should_match, _ = _expected_sets(expected)
    values = [
        float(item.get("semantic_score") or 0.0)
        for item in _top_k(recommendations, top_k)
        if _is_relevant(item, should_match)
    ]
    return mean(values) if values else 0.0


def confidence_distribution(recommendations: Iterable[dict[str, Any]]) -> dict[str, int]:
    counter = Counter(str(item.get("recommendation_confidence") or "LOW").upper() for item in recommendations)
    return {level: int(counter.get(level, 0)) for level in ("LOW", "MEDIUM", "HIGH")}


def confidence_calibration(recommendations: Iterable[dict[str, Any]], expected: ExpectedResult, top_k: int) -> dict[str, Any]:
    items = _top_k(recommendations, top_k)
    if not items:
        return {"score": 1.0, "status": "GOOD", "relevant_confidence": 0.0, "noise_confidence": 0.0}

    should_match, should_not_match = _expected_sets(expected)
    relevant_values = []
    noise_values = []
    for item in items:
        value = CONFIDENCE_VALUE.get(str(item.get("recommendation_confidence") or "LOW").upper(), 0.33)
        title = normalize_title(recommendation_title(item))
        if title in should_match:
            relevant_values.append(value)
        if title in should_not_match:
            noise_values.append(value)

    relevant_avg = mean(relevant_values) if relevant_values else 0.0
    noise_avg = mean(noise_values) if noise_values else 0.0
    if not noise_values:
        score = 1.0 if relevant_values else 0.75
    else:
        score = max(0.0, min(1.0, 0.5 + ((relevant_avg - noise_avg) / 2.0)))
    status = "GOOD" if score >= 0.70 else "MEDIUM" if score >= 0.50 else "LOW"
    return {
        "score": round(score, 4),
        "status": status,
        "relevant_confidence": round(relevant_avg, 4),
        "noise_confidence": round(noise_avg, 4),
    }


def recommendation_diversity(recommendations: Iterable[dict[str, Any]], top_k: int) -> float:
    items = _top_k(recommendations, top_k)
    if not items:
        return 0.0
    titles = {normalize_title(recommendation_title(item)) for item in items}
    companies = {normalize_title(item.get("company") or item.get("organisation_nom") or "") for item in items}
    non_empty_companies = {item for item in companies if item}
    return round(((len(titles) / len(items)) + (len(non_empty_companies) / len(items))) / 2.0, 4)


def metrics_for_recommendations(
    recommendations: Iterable[dict[str, Any]],
    expected: ExpectedResult,
    top_k: int,
) -> dict[str, Any]:
    items = _top_k(recommendations, top_k)
    return {
        "precision_at_k": round(precision_at_k(items, expected, top_k), 4),
        "recall_at_k": round(recall_at_k(items, expected, top_k), 4),
        "noise_rate": round(noise_rate(items, expected, top_k), 4),
        "exact_match_rate": round(exact_match_rate(items, expected, top_k), 4),
        "false_positive_rate": round(false_positive_rate(items, expected, top_k), 4),
        "mrr": round(mean_reciprocal_rank(items, expected, top_k), 4),
        "average_semantic_score": round(average_semantic_score(items, expected, top_k), 4),
        "confidence_calibration": confidence_calibration(items, expected, top_k),
        "recommendation_diversity": recommendation_diversity(items, top_k),
        "recommendation_count": len(items),
        "confidence_distribution": confidence_distribution(items),
    }


def aggregate_metric_dicts(rows: Iterable[dict[str, Any]]) -> dict[str, float]:
    rows = list(rows)
    if not rows:
        return {
            "precision_at_k": 0.0,
            "recall_at_k": 0.0,
            "noise_rate": 0.0,
            "exact_match_rate": 0.0,
            "false_positive_rate": 0.0,
            "recommendation_diversity": 0.0,
        }
    fields = (
        "precision_at_k",
        "recall_at_k",
        "noise_rate",
        "exact_match_rate",
        "false_positive_rate",
        "recommendation_diversity",
    )
    return {field: round(mean(float(row.get(field) or 0.0) for row in rows), 4) for field in fields}


def compute_crossencoder_uplift(
    baseline_reports: Iterable[dict[str, Any]],
    crossencoder_reports: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    baseline_rows = list(baseline_reports)
    crossencoder_rows = list(crossencoder_reports)
    if not baseline_rows or not crossencoder_rows:
        return _empty_crossencoder_uplift()

    pair_count = min(len(baseline_rows), len(crossencoder_rows))
    pairs = list(zip(baseline_rows[:pair_count], crossencoder_rows[:pair_count]))
    baseline_overall = aggregate_metric_dicts(row["metrics"] for row, _ in pairs)
    crossencoder_overall = aggregate_metric_dicts(row["metrics"] for _, row in pairs)

    baseline_top_3 = aggregate_metric_dicts(
        (row.get("top_3_metrics") or row["metrics"])
        for row, _ in pairs
    )
    crossencoder_top_3 = aggregate_metric_dicts(
        (row.get("top_3_metrics") or row["metrics"])
        for _, row in pairs
    )

    sparse_pairs = [
        (base, ce)
        for base, ce in pairs
        if _is_sparse_report(base)
    ]
    multilingual_pairs = [
        (base, ce)
        for base, ce in pairs
        if str(base.get("language") or "").upper() in {"AR", "FR", "MULTI"}
        or "multilingual" in base.get("categories", [])
    ]

    precision_delta = crossencoder_overall["precision_at_k"] - baseline_overall["precision_at_k"]
    false_positive_delta = (
        crossencoder_overall["false_positive_rate"] - baseline_overall["false_positive_rate"]
    )
    top_3_delta = crossencoder_top_3["precision_at_k"] - baseline_top_3["precision_at_k"]
    sparse_delta = _precision_delta_for_pairs(sparse_pairs)
    multilingual_delta = _precision_delta_for_pairs(multilingual_pairs)

    return {
        "scenario_count": pair_count,
        "baseline": baseline_overall,
        "crossencoder": crossencoder_overall,
        "precision_delta": round(precision_delta, 4),
        "precision_uplift_percent": _relative_percent(
            precision_delta,
            baseline_overall["precision_at_k"],
        ),
        "false_positive_rate_delta": round(false_positive_delta, 4),
        "false_positive_rate_delta_percent": round(false_positive_delta * 100.0, 2),
        "top_3_precision_delta": round(top_3_delta, 4),
        "top_3_precision_uplift_percent": _relative_percent(
            top_3_delta,
            baseline_top_3["precision_at_k"],
        ),
        "sparse_profile_precision_delta": round(sparse_delta, 4),
        "sparse_profile_uplift_percent": _relative_percent(
            sparse_delta,
            _average_precision(sparse_pairs, side="baseline"),
        ),
        "multilingual_precision_delta": round(multilingual_delta, 4),
        "multilingual_uplift_percent": _relative_percent(
            multilingual_delta,
            _average_precision(multilingual_pairs, side="baseline"),
        ),
    }


def status_for_precision_noise(precision: float, noise: float) -> str:
    if precision >= 0.70 and noise <= 0.10:
        return "GOOD"
    if precision >= 0.45 and noise <= 0.25:
        return "MEDIUM"
    return "LOW"


def _empty_crossencoder_uplift() -> dict[str, Any]:
    return {
        "scenario_count": 0,
        "baseline": aggregate_metric_dicts([]),
        "crossencoder": aggregate_metric_dicts([]),
        "precision_delta": 0.0,
        "precision_uplift_percent": 0.0,
        "false_positive_rate_delta": 0.0,
        "false_positive_rate_delta_percent": 0.0,
        "top_3_precision_delta": 0.0,
        "top_3_precision_uplift_percent": 0.0,
        "sparse_profile_precision_delta": 0.0,
        "sparse_profile_uplift_percent": 0.0,
        "multilingual_precision_delta": 0.0,
        "multilingual_uplift_percent": 0.0,
    }


def _is_sparse_report(row: dict[str, Any]) -> bool:
    categories = set(row.get("categories", []))
    return bool(categories.intersection({"sparse", "empty_profile", "role_only", "cv_only"}))


def _average_precision(pairs: list[tuple[dict[str, Any], dict[str, Any]]], *, side: str) -> float:
    if not pairs:
        return 0.0
    index = 0 if side == "baseline" else 1
    return mean(float(pair[index]["metrics"].get("precision_at_k") or 0.0) for pair in pairs)


def _precision_delta_for_pairs(pairs: list[tuple[dict[str, Any], dict[str, Any]]]) -> float:
    if not pairs:
        return 0.0
    return mean(
        float(ce["metrics"].get("precision_at_k") or 0.0)
        - float(base["metrics"].get("precision_at_k") or 0.0)
        for base, ce in pairs
    )


def _relative_percent(delta: float, baseline: float) -> float:
    return round((float(delta) / max(float(baseline or 0.0), 0.01)) * 100.0, 2)


def compute_cv_uplift(cv_pairs: Iterable[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    pairs = list(cv_pairs)
    if not pairs:
        return {
            "precision_delta": 0.0,
            "relative_precision_uplift": 0.0,
            "semantic_score_delta": 0.0,
            "noise_reduction": 0.0,
            "rank_improvement": 0.0,
            "role_specialization_improvement": 0.0,
            "status": "N/A",
        }

    precision_delta = mean(
        float(cv["metrics"]["precision_at_k"]) - float(base["metrics"]["precision_at_k"])
        for base, cv in pairs
    )
    base_precision = mean(float(base["metrics"]["precision_at_k"]) for base, _ in pairs)
    relative_precision = precision_delta / max(base_precision, 0.01)
    semantic_delta = mean(
        float(cv["metrics"]["average_semantic_score"]) - float(base["metrics"]["average_semantic_score"])
        for base, cv in pairs
    )
    noise_reduction = mean(
        float(base["metrics"]["noise_rate"]) - float(cv["metrics"]["noise_rate"])
        for base, cv in pairs
    )
    rank_improvement = mean(
        float(cv["metrics"]["mrr"]) - float(base["metrics"]["mrr"])
        for base, cv in pairs
    )
    specialization = mean(
        float(cv["metrics"]["exact_match_rate"]) - float(base["metrics"]["exact_match_rate"])
        for base, cv in pairs
    )
    status_score = precision_delta + semantic_delta + noise_reduction + rank_improvement
    status = "GOOD" if status_score > 0.10 else "MEDIUM" if status_score >= 0.0 else "LOW"
    return {
        "precision_delta": round(precision_delta, 4),
        "relative_precision_uplift": round(relative_precision, 4),
        "relative_precision_uplift_percent": round(relative_precision * 100.0, 2),
        "semantic_score_delta": round(semantic_delta, 4),
        "noise_reduction": round(noise_reduction, 4),
        "rank_improvement": round(rank_improvement, 4),
        "role_specialization_improvement": round(specialization, 4),
        "status": status,
        "scenario_count": len(pairs),
    }


def compute_sparse_profile_robustness(profile_reports: Iterable[dict[str, Any]]) -> dict[str, Any]:
    sparse_rows = [
        row for row in profile_reports
        if row.get("scenario") == "profile_only"
        and (
            "sparse" in row.get("categories", [])
            or "empty_profile" in row.get("categories", [])
            or "role_only" in row.get("categories", [])
            or "cv_only" in row.get("categories", [])
        )
    ]
    if not sparse_rows:
        return {"status": "N/A", "profile_count": 0}

    avg_noise = mean(float(row["metrics"]["noise_rate"]) for row in sparse_rows)
    avg_count = mean(float(row["metrics"]["recommendation_count"]) for row in sparse_rows)
    low_confidence_share = mean(
        (
            row["metrics"]["confidence_distribution"].get("LOW", 0)
            + row["metrics"]["confidence_distribution"].get("MEDIUM", 0)
        )
        / max(1, row["metrics"]["recommendation_count"])
        for row in sparse_rows
    )
    status = "GOOD" if avg_noise <= 0.10 and low_confidence_share >= 0.70 else "MEDIUM" if avg_noise <= 0.25 else "LOW"
    return {
        "status": status,
        "profile_count": len(sparse_rows),
        "average_noise_rate": round(avg_noise, 4),
        "average_recommendation_count": round(avg_count, 4),
        "low_or_medium_confidence_share": round(low_confidence_share, 4),
    }


def compute_multilingual_robustness(profile_reports: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows_by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in profile_reports:
        rows_by_language[str(row.get("language") or "UNK").upper()].append(row["metrics"])

    breakdown = {}
    for language, rows in sorted(rows_by_language.items()):
        aggregate = aggregate_metric_dicts(rows)
        aggregate["status"] = status_for_precision_noise(
            aggregate["precision_at_k"],
            aggregate["noise_rate"],
        )
        breakdown[language] = aggregate
    if not breakdown:
        return {"status": "N/A", "breakdown": {}}
    status_order = {"GOOD": 3, "MEDIUM": 2, "LOW": 1}
    weakest_language, weakest_metrics = min(
        breakdown.items(),
        key=lambda pair: status_order[pair[1]["status"]],
    )
    return {
        "status": weakest_metrics["status"],
        "breakdown": breakdown,
        "weakest_language": weakest_language,
    }


def _expected_semantic_terms(categories: Iterable[str]) -> set[str]:
    terms = set()
    for category in categories:
        terms.update(SEMANTIC_CATEGORY_TERMS.get(str(category), set()))
    return terms


def compute_semantic_extraction_metrics(profile_reports: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        row for row in profile_reports
        if row.get("semantic_resume") and row["semantic_resume"].get("has_structured_signal")
    ]
    if not rows:
        return {
            "cv_semantic_uplift": 0.0,
            "semantic_extraction_precision": 0.0,
            "extracted_skill_relevance": 0.0,
            "multilingual_extraction_robustness": "N/A",
            "scenario_count": 0,
        }

    precision_scores = []
    relevance_hits = []
    multilingual_scores = []
    for row in rows:
        semantic_resume = row["semantic_resume"]
        extracted = {
            normalize_title(value)
            for field in ("skills", "domains", "tools")
            for value in semantic_resume.get(field, [])
        }
        expected = {normalize_title(value) for value in _expected_semantic_terms(row.get("categories", []))}
        if extracted and expected:
            precision_scores.append(len(extracted.intersection(expected)) / len(extracted))
            relevance_hits.append(1.0 if extracted.intersection(expected) else 0.0)
        elif extracted:
            precision_scores.append(0.0)
            relevance_hits.append(0.0)

        language = str(row.get("language") or "").upper()
        if language in {"AR", "FR", "MULTI"}:
            multilingual_scores.append(1.0 if semantic_resume.get("has_structured_signal") else 0.0)

    precision = mean(precision_scores) if precision_scores else 0.0
    relevance = mean(relevance_hits) if relevance_hits else 0.0
    multilingual = mean(multilingual_scores) if multilingual_scores else 0.0
    multilingual_status = "GOOD" if multilingual >= 0.80 else "MEDIUM" if multilingual >= 0.50 else "LOW"
    return {
        "cv_semantic_uplift": round(relevance, 4),
        "semantic_extraction_precision": round(precision, 4),
        "extracted_skill_relevance": round(relevance, 4),
        "multilingual_extraction_robustness": multilingual_status,
        "multilingual_extraction_score": round(multilingual, 4),
        "scenario_count": len(rows),
    }
