from __future__ import annotations

import re
from collections.abc import Callable

from seektalent.models import ControllerContext, FinalizeContext, ReflectionContext, ScoredCandidate, SearchAttempt
from seektalent.models import scored_candidate_sort_key
from seektalent.requirements import build_requirement_digest
from seektalent.tracing import json_char_count, json_sha256


def _preview_text(text: str, *, limit: int) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[:limit].rstrip()}..."


def slim_controller_context(
    *,
    context: ControllerContext,
    input_text_refs_builder: Callable[..., dict[str, object]],
) -> dict[str, object]:
    digest = context.requirement_digest or build_requirement_digest(context.requirement_sheet)
    return {
        "schema_version": "v0.2.3a",
        "context_type": "controller",
        "round_no": context.round_no,
        "input": input_text_refs_builder(
            role_title=context.requirement_sheet.role_title,
            jd=context.full_jd,
            notes=context.full_notes,
        ),
        "refs": {
            "requirement_sheet": "requirement_sheet.json",
            "sent_query_history": "sent_query_history.json",
        },
        "budget": {
            "min_rounds": context.min_rounds,
            "max_rounds": context.max_rounds,
            "retrieval_rounds_completed": context.retrieval_rounds_completed,
            "rounds_remaining_after_current": context.rounds_remaining_after_current,
            "budget_used_ratio": context.budget_used_ratio,
            "near_budget_limit": context.near_budget_limit,
            "is_final_allowed_round": context.is_final_allowed_round,
            "target_new": context.target_new,
            "budget_reminder": context.budget_reminder,
        },
        "stop_guidance": context.stop_guidance.model_dump(mode="json"),
        "requirement_digest": digest.model_dump(mode="json"),
        "query_term_pool": [item.model_dump(mode="json") for item in context.query_term_pool],
        "current_top_pool": [item.model_dump(mode="json") for item in context.current_top_pool],
        "latest_search_observation": (
            context.latest_search_observation.model_dump(mode="json")
            if context.latest_search_observation is not None
            else None
        ),
        "previous_reflection": (
            context.previous_reflection.model_dump(mode="json") if context.previous_reflection is not None else None
        ),
        "latest_reflection_keyword_advice": (
            context.latest_reflection_keyword_advice.model_dump(mode="json")
            if context.latest_reflection_keyword_advice is not None
            else None
        ),
        "latest_reflection_filter_advice": (
            context.latest_reflection_filter_advice.model_dump(mode="json")
            if context.latest_reflection_filter_advice is not None
            else None
        ),
        "shortage_history": context.shortage_history,
    }


def slim_reflection_context(
    *,
    context: ReflectionContext,
    input_text_refs_builder: Callable[..., dict[str, object]],
    slim_search_attempt: Callable[[SearchAttempt], dict[str, object]],
    slim_scored_candidate: Callable[..., dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": "v0.2.3a",
        "context_type": "reflection",
        "round_no": context.round_no,
        "input": input_text_refs_builder(
            role_title=context.requirement_sheet.role_title,
            jd=context.full_jd,
            notes=context.full_notes,
        ),
        "refs": {
            "requirement_sheet": "requirement_sheet.json",
            "sent_query_history": "sent_query_history.json",
        },
        "requirement_digest": build_requirement_digest(context.requirement_sheet).model_dump(mode="json"),
        "query_term_pool": [item.model_dump(mode="json") for item in context.query_term_pool],
        "current_retrieval_plan": context.current_retrieval_plan.model_dump(mode="json"),
        "search_observation": context.search_observation.model_dump(mode="json"),
        "search_attempts": [slim_search_attempt(item) for item in context.search_attempts],
        "top_candidates": [
            slim_scored_candidate(candidate, rank=index)
            for index, candidate in enumerate(context.top_candidates[:8], start=1)
        ],
        "dropped_candidates": [
            slim_scored_candidate(candidate, rank=index)
            for index, candidate in enumerate(context.dropped_candidates[:5], start=1)
        ],
        "scoring_failures": [item.model_dump(mode="json") for item in context.scoring_failures],
        "sent_query_count": len(context.sent_query_history),
    }


def slim_finalize_context(
    *,
    context: FinalizeContext,
    slim_scored_candidate: Callable[..., dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": "v0.2.3a",
        "context_type": "finalize",
        "run_id": context.run_id,
        "run_dir": context.run_dir,
        "rounds_executed": context.rounds_executed,
        "stop_reason": context.stop_reason,
        "refs": {
            "requirement_sheet": "requirement_sheet.json",
            "sent_query_history": "sent_query_history.json",
            "scorecards": "rounds/*/scorecards.jsonl",
            "top_pool_snapshots": "rounds/*/top_pool_snapshot.json",
        },
        "requirement_digest": (
            context.requirement_digest.model_dump(mode="json")
            if context.requirement_digest is not None
            else None
        ),
        "top_candidates": [
            slim_scored_candidate(candidate, rank=index)
            for index, candidate in enumerate(context.top_candidates, start=1)
        ],
        "sent_query_count": len(context.sent_query_history),
    }


def slim_search_attempt(attempt: SearchAttempt) -> dict[str, object]:
    payload = attempt.model_dump(mode="json")
    request_payload = payload.pop("request_payload", {})
    payload["request_payload_sha256"] = json_sha256(request_payload)
    payload["request_payload_chars"] = json_char_count(request_payload)
    return payload


def slim_scored_candidate(candidate: ScoredCandidate, *, rank: int | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "resume_id": candidate.resume_id,
        "fit_bucket": candidate.fit_bucket,
        "overall_score": candidate.overall_score,
        "must_have_match_score": candidate.must_have_match_score,
        "preferred_match_score": candidate.preferred_match_score,
        "risk_score": candidate.risk_score,
        "source_round": candidate.source_round,
        "sort_key": list(scored_candidate_sort_key(candidate)),
        "matched_must_haves": candidate.matched_must_haves[:3],
        "missing_must_haves": candidate.missing_must_haves[:1],
        "matched_preferences": candidate.matched_preferences[:1],
        "negative_signals": candidate.negative_signals[:1],
        "risk_flags": candidate.risk_flags[:1],
        "reasoning_summary": _preview_text(candidate.reasoning_summary, limit=80),
    }
    if rank is not None:
        payload["rank"] = rank
    return payload


def slim_top_pool_snapshot(candidates: list[ScoredCandidate]) -> list[dict[str, object]]:
    return [
        {
            "resume_id": candidate.resume_id,
            "rank": index,
            "fit_bucket": candidate.fit_bucket,
            "overall_score": candidate.overall_score,
            "must_have_match_score": candidate.must_have_match_score,
            "risk_score": candidate.risk_score,
            "source_round": candidate.source_round,
            "sort_key": list(scored_candidate_sort_key(candidate)),
        }
        for index, candidate in enumerate(candidates, start=1)
    ]
