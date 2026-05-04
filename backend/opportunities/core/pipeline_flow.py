"""
Business flow for a single raw opportunity.

This module names the data pipeline separately from the source scheduler in
``opportunities.pipeline``:

raw -> normalization -> enrichment -> scoring -> materialization
"""

from typing import Any

from opportunities.enrichment import enrich_opportunity_text
from opportunities.materialization import materialize_opportunity
from opportunities.normalization import normalize_raw_opportunity
from opportunities.quality.quality_gate import evaluate_opportunity


def process_opportunity(raw: Any):
    """
    Business pipeline:
    raw -> normalization -> enrichment -> scoring -> materialization
    """

    normalized_data = normalize_raw_opportunity(raw)
    normalized_data.update(enrich_opportunity_text(normalized_data))
    scored_data = evaluate_opportunity(normalized_data)
    if not scored_data.get("is_usable", True):
        reason = scored_data.get("unusable_reason") or "quality_gate_rejected"
        raise ValueError(f"Quality gate rejected record: {reason}")
    return materialize_opportunity(scored_data)
