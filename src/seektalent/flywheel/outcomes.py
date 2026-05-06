from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from typing import Any

from seektalent.flywheel.store import canonical_json
from seektalent.models import QueryOutcomeClassification, QueryOutcomeThresholds
from seektalent.runtime.runtime_diagnostics import classify_query_outcome

QUERY_OUTCOME_SCHEMA_VERSION = "query-outcome-v1"
QUERY_OUTCOME_POLICY_VERSION = "query-outcome-policy-v1"
DEDUPE_VERSION = "dedupe-v1"


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def build_runtime_query_outcome_row(
    *,
    run_id: str,
    query_instance_id: str,
    query_fingerprint: str,
    round_no: int,
    lane_type: str,
    provider_returned_count: int,
    new_unique_resume_count: int,
    duplicate_count: int,
    scored_resume_count: int,
    new_fit_count: int,
    must_have_match_scores: list[float],
    risk_scores: list[float],
    off_intent_reason_count: int,
    classification: QueryOutcomeClassification,
    thresholds_payload: dict[str, Any],
) -> dict[str, object]:
    thresholds_json = canonical_json(thresholds_payload)
    return {
        "run_id": run_id,
        "query_instance_id": query_instance_id,
        "query_fingerprint": query_fingerprint,
        "outcome_schema_version": QUERY_OUTCOME_SCHEMA_VERSION,
        "outcome_policy_version": QUERY_OUTCOME_POLICY_VERSION,
        "outcome_thresholds_hash": sha256(thresholds_json.encode("utf-8")).hexdigest(),
        "outcome_thresholds_json": thresholds_json,
        "scoring_policy_version": None,
        "dedupe_version": DEDUPE_VERSION,
        "outcome_basis": "runtime_score",
        "round_no": round_no,
        "lane_type": lane_type,
        "provider_returned_count": provider_returned_count,
        "new_unique_resume_count": new_unique_resume_count,
        "duplicate_count": duplicate_count,
        "scored_resume_count": scored_resume_count,
        "new_fit_count": new_fit_count,
        "new_near_fit_count": 0,
        "fit_rate_denominator": "scored_resume_count" if scored_resume_count else None,
        "fit_rate": new_fit_count / scored_resume_count if scored_resume_count else None,
        "must_have_match_avg": _avg(must_have_match_scores),
        "risk_score_avg": _avg(risk_scores),
        "off_intent_reason_count": off_intent_reason_count,
        "primary_label": classification.primary_label,
        "labels_json": canonical_json(classification.labels),
        "reasons_json": canonical_json(classification.reasons),
        "latency_ms": None,
        "cost_estimate_usd": None,
        "artifact_ref_id": None,
    }


def build_runtime_query_outcome_rows_from_hits(
    *,
    run_id: str,
    hits: list[dict[str, Any]],
    thresholds_payload: dict[str, Any] | None = None,
) -> list[dict[str, object]]:
    thresholds_payload = thresholds_payload or QueryOutcomeThresholds().model_dump(mode="json")
    thresholds = QueryOutcomeThresholds.model_validate(thresholds_payload)
    hits_by_query: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for hit in hits:
        hits_by_query[str(hit["query_instance_id"])].append(hit)

    rows: list[dict[str, object]] = []
    for query_instance_id, query_hits in sorted(hits_by_query.items()):
        provider_returned_count = len(query_hits)
        new_hits = [hit for hit in query_hits if bool(hit.get("was_new_to_pool"))]
        scored_hits = [hit for hit in new_hits if hit.get("scored_fit_bucket") is not None]
        must_have_scores = [
            float(hit["must_have_match_score"]) for hit in scored_hits if hit.get("must_have_match_score") is not None
        ]
        risk_scores = [float(hit["risk_score"]) for hit in scored_hits if hit.get("risk_score") is not None]
        new_fit_count = sum(1 for hit in scored_hits if hit.get("scored_fit_bucket") == "fit")
        scored_resume_count = len(scored_hits)
        must_have_match_avg = _avg(must_have_scores) or 0.0
        fit_rate = new_fit_count / scored_resume_count if scored_resume_count else 0.0
        off_intent_reason_count = sum(int(hit.get("off_intent_reason_count") or 0) for hit in scored_hits)
        classification = classify_query_outcome(
            provider_returned_count=provider_returned_count,
            new_unique_resume_count=len(new_hits),
            new_fit_or_near_fit_count=new_fit_count,
            fit_rate=fit_rate,
            must_have_match_avg=must_have_match_avg,
            exploit_baseline_must_have_match_avg=must_have_match_avg,
            off_intent_reason_count=off_intent_reason_count,
            thresholds=thresholds,
        )
        first_hit = query_hits[0]
        rows.append(
            build_runtime_query_outcome_row(
                run_id=run_id,
                query_instance_id=query_instance_id,
                query_fingerprint=str(first_hit["query_fingerprint"]),
                round_no=int(first_hit["round_no"]),
                lane_type=str(first_hit["lane_type"]),
                provider_returned_count=provider_returned_count,
                new_unique_resume_count=len(new_hits),
                duplicate_count=sum(1 for hit in query_hits if bool(hit.get("was_duplicate"))),
                scored_resume_count=scored_resume_count,
                new_fit_count=new_fit_count,
                must_have_match_scores=must_have_scores,
                risk_scores=risk_scores,
                off_intent_reason_count=off_intent_reason_count,
                classification=classification,
                thresholds_payload=thresholds_payload,
            )
        )
    return rows
