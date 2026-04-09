from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from seektalent.models import SearchRunBundle, SearchRunEval, SearchRunEvalMetric


PHASE6_STATUS = "phase6_offline_artifacts_active"


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def utc_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_run_id(*, job_description_sha256: str, created_at_utc: datetime) -> str:
    return f"{utc_timestamp(created_at_utc)}_{job_description_sha256[:8]}"


def build_search_run_eval(bundle: SearchRunBundle) -> SearchRunEval:
    search_rounds = [round_artifact for round_artifact in bundle.rounds if round_artifact.execution_result]
    scored_rows = [
        row
        for round_artifact in bundle.rounds
        if round_artifact.scoring_result is not None
        for row in round_artifact.scoring_result.scored_candidates
    ]
    total_runtime_audit_tags = sum(
        len(tags)
        for round_artifact in bundle.rounds
        for tags in round_artifact.runtime_audit_tags.values()
    )
    metrics = [
        SearchRunEvalMetric(
            name="routing_mode",
            value=bundle.bootstrap.routing_result.routing_mode,
        ),
        SearchRunEvalMetric(
            name="selected_knowledge_pack_id",
            value=bundle.bootstrap.routing_result.selected_knowledge_pack_id or "",
        ),
        SearchRunEvalMetric(
            name="routing_confidence",
            value=bundle.bootstrap.routing_result.routing_confidence,
        ),
        SearchRunEvalMetric(name="round_count", value=len(bundle.rounds)),
        SearchRunEvalMetric(name="search_round_count", value=len(search_rounds)),
        SearchRunEvalMetric(
            name="stop_reason",
            value=bundle.final_result.stop_reason,
        ),
        SearchRunEvalMetric(
            name="final_shortlist_count",
            value=len(bundle.final_result.final_shortlist_candidate_ids),
        ),
        SearchRunEvalMetric(
            name="top_candidate_id",
            value=(
                bundle.final_result.final_shortlist_candidate_ids[0]
                if bundle.final_result.final_shortlist_candidate_ids
                else ""
            ),
        ),
        SearchRunEvalMetric(
            name="total_pages_fetched",
            value=sum(
                round_artifact.execution_result.search_page_statistics.pages_fetched
                for round_artifact in search_rounds
            ),
        ),
        SearchRunEvalMetric(
            name="deduplicated_candidate_count",
            value=sum(
                len(round_artifact.execution_result.deduplicated_candidates)
                for round_artifact in search_rounds
            ),
        ),
        SearchRunEvalMetric(
            name="average_novelty",
            value=(
                0.0
                if not bundle.rounds
                else sum(
                    round_artifact.branch_evaluation.novelty_score
                    for round_artifact in bundle.rounds
                    if round_artifact.branch_evaluation is not None
                )
                / max(
                    1,
                    sum(
                        1
                        for round_artifact in bundle.rounds
                        if round_artifact.branch_evaluation is not None
                    ),
                )
            ),
        ),
        SearchRunEvalMetric(
            name="average_usefulness",
            value=(
                0.0
                if not bundle.rounds
                else sum(
                    round_artifact.branch_evaluation.usefulness_score
                    for round_artifact in bundle.rounds
                    if round_artifact.branch_evaluation is not None
                )
                / max(
                    1,
                    sum(
                        1
                        for round_artifact in bundle.rounds
                        if round_artifact.branch_evaluation is not None
                    ),
                )
            ),
        ),
        SearchRunEvalMetric(
            name="average_stability_risk",
            value=(
                0.0
                if not scored_rows
                else sum(row.risk_score for row in scored_rows) / len(scored_rows)
            ),
        ),
        SearchRunEvalMetric(
            name="runtime_audit_tag_count",
            value=total_runtime_audit_tags,
        ),
        SearchRunEvalMetric(
            name="llm_validator_retry_count",
            value=(
                bundle.bootstrap.requirement_extraction_audit.validator_retry_count
                + bundle.bootstrap.bootstrap_keyword_generation_audit.validator_retry_count
                + bundle.finalization_audit.validator_retry_count
                + sum(round_artifact.controller_audit.validator_retry_count for round_artifact in bundle.rounds)
                + sum(
                    round_artifact.branch_evaluation_audit.validator_retry_count
                    for round_artifact in bundle.rounds
                    if round_artifact.branch_evaluation_audit is not None
                )
            ),
        ),
    ]
    return SearchRunEval(experiment_id="E5", run_id=bundle.run_id, metrics=metrics)


def write_run_bundle(bundle: SearchRunBundle, *, runs_root: Path) -> Path:
    run_dir = runs_root / bundle.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "bundle.json", bundle.model_dump(mode="json"))
    _write_json(
        run_dir / "final_result.json",
        bundle.final_result.model_dump(mode="json"),
    )
    if bundle.eval is not None:
        _write_json(run_dir / "eval.json", bundle.eval.model_dump(mode="json"))
    return run_dir


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "PHASE6_STATUS",
    "build_run_id",
    "build_search_run_eval",
    "utc_isoformat",
    "utc_now",
    "write_run_bundle",
]
