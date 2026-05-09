from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any


DEFAULT_CONFIG_MODULE = "tests.recommendation_benchmark.benchmark_config"


@dataclass(frozen=True)
class BenchmarkProfile:
    profile_id: str
    language: str
    categories: tuple[str, ...]
    fields: dict[str, Any]
    cv_variant_ids: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class BenchmarkResume:
    resume_id: str
    language: str
    specialization: str
    text: str


@dataclass(frozen=True)
class ExpectedResult:
    profile_id: str
    should_match: tuple[str, ...]
    should_not_match: tuple[str, ...]
    cv_expectations: dict[str, dict[str, tuple[str, ...]]] = field(default_factory=dict)

    def for_resume(self, resume_id: str | None = None) -> "ExpectedResult":
        if not resume_id:
            return self
        override = self.cv_expectations.get(resume_id)
        if not override:
            return self
        return ExpectedResult(
            profile_id=self.profile_id,
            should_match=override.get("should_match", self.should_match),
            should_not_match=override.get("should_not_match", self.should_not_match),
            cv_expectations={},
        )


@dataclass(frozen=True)
class BenchmarkOpportunity:
    opportunity_id: str
    title: str
    description: str
    company: str
    location: str
    language: str
    skills: tuple[str, ...]
    industries: tuple[str, ...]
    confusing: bool = False
    type_opportunite: str = "EMPLOI"
    contract_type: str = "CDI"
    availability: str = "Hybrid"
    experience_min: int | None = None
    experience_max: int | None = None


@dataclass(frozen=True)
class BenchmarkDataset:
    profiles: tuple[BenchmarkProfile, ...]
    resumes: dict[str, BenchmarkResume]
    expected: dict[str, ExpectedResult]
    opportunities: tuple[BenchmarkOpportunity, ...]
    report_dir: Path
    default_top_k: int
    precision_good_threshold: float
    precision_medium_threshold: float

    def expectation_for(self, profile_id: str, resume_id: str | None = None) -> ExpectedResult:
        expected = self.expected[profile_id]
        return expected.for_resume(resume_id)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value if str(item).strip())


def _load_config(config_module: str | ModuleType = DEFAULT_CONFIG_MODULE) -> ModuleType:
    if isinstance(config_module, ModuleType):
        return config_module
    return importlib.import_module(config_module)


def load_benchmark_dataset(config_module: str | ModuleType = DEFAULT_CONFIG_MODULE) -> BenchmarkDataset:
    config = _load_config(config_module)
    profiles_payload = _load_json(Path(config.PROFILES_PATH))
    resumes_payload = _load_json(Path(config.RESUMES_PATH))
    expected_payload = _load_json(Path(config.EXPECTED_RESULTS_PATH))
    opportunities_payload = _load_json(Path(config.OPPORTUNITIES_PATH))

    profiles = tuple(
        BenchmarkProfile(
            profile_id=item["profile_id"],
            language=item.get("language", "EN"),
            categories=_as_tuple(item.get("categories")),
            fields=dict(item.get("fields") or {}),
            cv_variant_ids=_as_tuple(item.get("cv_variant_ids")),
            notes=str(item.get("notes") or ""),
        )
        for item in profiles_payload
    )
    resumes = {
        item["resume_id"]: BenchmarkResume(
            resume_id=item["resume_id"],
            language=item.get("language", "EN"),
            specialization=item.get("specialization", ""),
            text=item.get("text", ""),
        )
        for item in resumes_payload
    }
    expected = {}
    for item in expected_payload:
        cv_expectations = {}
        for resume_id, expectation in (item.get("cv_expectations") or {}).items():
            cv_expectations[resume_id] = {
                "should_match": _as_tuple(expectation.get("should_match")),
                "should_not_match": _as_tuple(expectation.get("should_not_match")),
            }
        expected[item["profile_id"]] = ExpectedResult(
            profile_id=item["profile_id"],
            should_match=_as_tuple(item.get("should_match")),
            should_not_match=_as_tuple(item.get("should_not_match")),
            cv_expectations=cv_expectations,
        )
    opportunities = tuple(
        BenchmarkOpportunity(
            opportunity_id=item["opportunity_id"],
            title=item["title"],
            description=item["description"],
            company=item.get("company", "BidWise Benchmark"),
            location=item.get("location", "Tunis"),
            language=item.get("language", "EN"),
            skills=_as_tuple(item.get("skills")),
            industries=_as_tuple(item.get("industries")),
            confusing=bool(item.get("confusing", False)),
            type_opportunite=item.get("type_opportunite", "EMPLOI"),
            contract_type=item.get("contract_type", "CDI"),
            availability=item.get("availability", "Hybrid"),
            experience_min=item.get("experience_min"),
            experience_max=item.get("experience_max"),
        )
        for item in opportunities_payload
    )

    profile_ids = {profile.profile_id for profile in profiles}
    missing_expected = sorted(profile_ids.difference(expected))
    if missing_expected:
        raise ValueError(f"Benchmark profiles missing expected results: {', '.join(missing_expected)}")

    missing_resumes = sorted(
        resume_id
        for profile in profiles
        for resume_id in profile.cv_variant_ids
        if resume_id not in resumes
    )
    if missing_resumes:
        raise ValueError(f"Benchmark profiles reference unknown resumes: {', '.join(missing_resumes)}")

    return BenchmarkDataset(
        profiles=profiles,
        resumes=resumes,
        expected=expected,
        opportunities=opportunities,
        report_dir=Path(config.BENCHMARK_REPORT_DIR),
        default_top_k=int(getattr(config, "DEFAULT_TOP_K", 10)),
        precision_good_threshold=float(getattr(config, "PRECISION_GOOD_THRESHOLD", 0.70)),
        precision_medium_threshold=float(getattr(config, "PRECISION_MEDIUM_THRESHOLD", 0.45)),
    )

