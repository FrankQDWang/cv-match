from pathlib import Path

import pytest
from pydantic import ValidationError

from cv_match.config import AppSettings
from cv_match.models import (
    CTSQuery,
    ControllerDecision,
    HardConstraintSlots,
    InputTruth,
    LocationExecutionPlan,
    ProposedFilterPlan,
    QueryTermCandidate,
    ReflectionAdvice,
    ReflectionFilterAdvice,
    ReflectionKeywordAdvice,
    RequirementSheet,
    RetrievalState,
    RoundRetrievalPlan,
    RoundState,
    RunState,
    ScoringPolicy,
)
from cv_match.runtime import WorkflowRuntime


def _requirement_sheet() -> RequirementSheet:
    return RequirementSheet(
        role_title="Senior Python Engineer",
        role_summary="Build resume matching workflows.",
        must_have_capabilities=["python", "retrieval"],
        hard_constraints=HardConstraintSlots(locations=["上海市"]),
        initial_query_term_pool=[
            QueryTermCandidate(
                term="python",
                source="jd",
                category="role_anchor",
                priority=1,
                evidence="JD title",
                first_added_round=0,
            ),
            QueryTermCandidate(
                term="resume matching",
                source="notes",
                category="domain",
                priority=2,
                evidence="Notes mention resume matching.",
                first_added_round=0,
            ),
        ],
        scoring_rationale="Score Python fit first.",
    )


def _run_state_with_previous_reflection() -> RunState:
    requirement_sheet = _requirement_sheet()
    return RunState(
        input_truth=InputTruth(
            jd="JD text",
            notes="Notes text",
            jd_sha256="jd-hash",
            notes_sha256="notes-hash",
        ),
        requirement_sheet=requirement_sheet,
        scoring_policy=ScoringPolicy(
            role_title=requirement_sheet.role_title,
            role_summary=requirement_sheet.role_summary,
            must_have_capabilities=requirement_sheet.must_have_capabilities,
            preferred_capabilities=[],
            exclusion_signals=[],
            hard_constraints=requirement_sheet.hard_constraints,
            preferences=requirement_sheet.preferences,
            scoring_rationale=requirement_sheet.scoring_rationale,
        ),
        retrieval_state=RetrievalState(
            current_plan_version=1,
            query_term_pool=requirement_sheet.initial_query_term_pool,
        ),
        round_history=[
            RoundState(
                round_no=1,
                controller_decision=ControllerDecision(
                    thought_summary="Round 1 search.",
                    action="search_cts",
                    decision_rationale="Need initial recall.",
                    proposed_query_terms=["python", "resume matching"],
                    proposed_filter_plan=ProposedFilterPlan(),
                ),
                retrieval_plan=RoundRetrievalPlan(
                    plan_version=1,
                    round_no=1,
                    query_terms=["python", "resume matching"],
                    keyword_query='python "resume matching"',
                    projected_cts_filters={},
                    runtime_only_constraints=[],
                    location_execution_plan=LocationExecutionPlan(
                        mode="single",
                        allowed_locations=["上海市"],
                        preferred_locations=[],
                        priority_order=[],
                        balanced_order=["上海市"],
                        rotation_offset=0,
                        target_new=10,
                    ),
                    target_new=10,
                    rationale="Round 1 query.",
                ),
                cts_queries=[
                    CTSQuery(
                        query_terms=["python", "resume matching"],
                        keyword_query='python "resume matching"',
                        native_filters={"location": ["上海市"]},
                        rationale="Round 1 query.",
                    )
                ],
                reflection_advice=ReflectionAdvice(
                    strategy_assessment="Need one more domain term.",
                    quality_assessment="Top pool is acceptable.",
                    coverage_assessment="Coverage is still narrow.",
                    keyword_advice=ReflectionKeywordAdvice(suggested_add_terms=["trace"]),
                    filter_advice=ReflectionFilterAdvice(suggested_keep_filter_fields=["position"]),
                    suggest_stop=False,
                    reflection_summary="Continue and widen the domain surface.",
                ),
            )
        ],
    )


def test_controller_decision_requires_proposals_for_search() -> None:
    with pytest.raises(ValidationError):
        ControllerDecision(
            thought_summary="Search.",
            action="search_cts",
            decision_rationale="Need recall.",
        )


def test_controller_decision_rejects_stop_with_search_fields() -> None:
    with pytest.raises(ValidationError):
        ControllerDecision(
            thought_summary="Stop.",
            action="stop",
            decision_rationale="Enough signal.",
            proposed_query_terms=["python"],
            stop_reason="controller_stop",
        )


def test_controller_decision_rejects_unknown_filter_fields() -> None:
    with pytest.raises(ValidationError):
        ProposedFilterPlan(optional_filters={"unsupported_field": ["custom"]})


def test_runtime_requires_response_to_reflection_after_previous_round() -> None:
    settings = AppSettings(_env_file=None).with_overrides(runs_dir=str(Path.cwd() / ".tmp-runs"), mock_cts=True)
    runtime = WorkflowRuntime(settings)
    run_state = _run_state_with_previous_reflection()
    decision = ControllerDecision(
        thought_summary="Search again.",
        action="search_cts",
        decision_rationale="Add one more term.",
        proposed_query_terms=["python", "resume matching", "trace"],
        proposed_filter_plan=ProposedFilterPlan(optional_filters={"position": "Senior Python Engineer"}),
    )

    with pytest.raises(ValueError, match="response_to_reflection"):
        runtime._sanitize_controller_decision(decision=decision, run_state=run_state, round_no=2)
