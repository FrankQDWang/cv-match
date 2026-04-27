from seektalent.models import RoundRetrievalPlan, SecondLaneDecision
from seektalent.retrieval import build_location_execution_plan
from seektalent.runtime.second_lane_runtime import build_second_lane_decision


def _retrieval_plan(*, query_terms: list[str]) -> RoundRetrievalPlan:
    return RoundRetrievalPlan(
        plan_version=2,
        round_no=2,
        query_terms=query_terms,
        keyword_query=" ".join(query_terms),
        projected_provider_filters={},
        runtime_only_constraints=[],
        location_execution_plan=build_location_execution_plan(
            allowed_locations=["shanghai"],
            preferred_locations=["shanghai"],
            round_no=2,
            target_new=6,
        ),
        target_new=6,
        rationale="test",
    )


def test_build_second_lane_decision_falls_back_to_generic_when_prf_policy_is_unavailable() -> None:
    retrieval_plan = _retrieval_plan(query_terms=["python", "ranking"])

    decision, lane = build_second_lane_decision(
        round_no=2,
        retrieval_plan=retrieval_plan,
        query_term_pool=[],
        sent_query_history=[],
        prf_decision=None,
        run_id="run-a",
        job_intent_fingerprint="job-1",
        source_plan_version="2",
    )

    assert decision == SecondLaneDecision(
        round_no=2,
        attempted_prf=True,
        prf_gate_passed=False,
        selected_lane_type="generic_explore",
        selected_query_instance_id=decision.selected_query_instance_id,
        selected_query_fingerprint=decision.selected_query_fingerprint,
        reject_reasons=["prf_policy_not_available"],
        fallback_lane_type="generic_explore",
        fallback_query_fingerprint=decision.selected_query_fingerprint,
        prf_policy_version="unavailable",
        generic_explore_version="v1",
    )
    assert lane is not None
    assert lane.lane_type == "generic_explore"
