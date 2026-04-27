from __future__ import annotations

from typing import Any

from seektalent.models import QueryTermCandidate, RoundRetrievalPlan, SecondLaneDecision, SentQueryRecord
from seektalent.retrieval import derive_explore_query_terms
from seektalent.runtime.retrieval_runtime import LogicalQueryState, build_logical_query_state


def _fallback_explore_terms(
    *,
    retrieval_plan: RoundRetrievalPlan,
    query_term_pool: list[QueryTermCandidate],
    sent_query_history: list[SentQueryRecord],
) -> list[str] | None:
    try:
        return derive_explore_query_terms(
            retrieval_plan.query_terms,
            title_anchor_terms=[],
            query_term_pool=query_term_pool,
            sent_query_history=sent_query_history,
        )
    except ValueError:
        if query_term_pool:
            raise
        return list(retrieval_plan.query_terms)


def build_second_lane_decision(
    *,
    round_no: int,
    retrieval_plan: RoundRetrievalPlan,
    query_term_pool: list[QueryTermCandidate],
    sent_query_history: list[SentQueryRecord],
    prf_decision: Any | None,
    run_id: str,
    job_intent_fingerprint: str,
    source_plan_version: str,
) -> tuple[SecondLaneDecision, LogicalQueryState | None]:
    del prf_decision
    if round_no == 1 or len(retrieval_plan.query_terms) <= 1:
        return (
            SecondLaneDecision(
                round_no=round_no,
                attempted_prf=False,
                prf_gate_passed=False,
                reject_reasons=["round_one_or_anchor_only"],
                no_fetch_reason="single_lane_round",
                prf_policy_version="unavailable",
            ),
            None,
        )

    explore_terms = _fallback_explore_terms(
        retrieval_plan=retrieval_plan,
        query_term_pool=query_term_pool,
        sent_query_history=sent_query_history,
    )
    if not explore_terms:
        return (
            SecondLaneDecision(
                round_no=round_no,
                attempted_prf=True,
                prf_gate_passed=False,
                reject_reasons=["prf_policy_not_available"],
                no_fetch_reason="no_generic_explore_query",
                prf_policy_version="unavailable",
                generic_explore_version="v1",
            ),
            None,
        )

    query_state = build_logical_query_state(
        run_id=run_id,
        round_no=round_no,
        lane_type="generic_explore",
        query_terms=explore_terms,
        job_intent_fingerprint=job_intent_fingerprint,
        source_plan_version=source_plan_version,
    )
    return (
        SecondLaneDecision(
            round_no=round_no,
            attempted_prf=True,
            prf_gate_passed=False,
            selected_lane_type="generic_explore",
            selected_query_instance_id=query_state.query_instance_id,
            selected_query_fingerprint=query_state.query_fingerprint,
            reject_reasons=["prf_policy_not_available"],
            fallback_lane_type="generic_explore",
            fallback_query_fingerprint=query_state.query_fingerprint,
            prf_policy_version="unavailable",
            generic_explore_version="v1",
        ),
        query_state,
    )
