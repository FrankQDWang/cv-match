from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace

from pydantic_ai.models.test import TestModel

from seektalent.bootstrap_assets import default_bootstrap_assets
from seektalent.clients.cts_client import CTSFetchResult
from seektalent.config import AppSettings
from seektalent.models import RetrievedCandidate_t, StopGuardThresholds
from seektalent.runtime.orchestrator import WorkflowRuntime
from seektalent_rerank.models import RerankResponse, RerankResult


def _requirement_draft_payload() -> dict[str, object]:
    return {
        "role_title_candidate": "Senior Python / LLM Engineer",
        "role_summary_candidate": "Build Python and retrieval systems.",
        "must_have_capability_candidates": [
            "Python backend",
            "LLM application",
            "retrieval or ranking experience",
        ],
        "preferred_capability_candidates": ["workflow orchestration"],
        "exclusion_signal_candidates": ["data analyst"],
        "preference_candidates": {
            "preferred_domains": [],
            "preferred_backgrounds": [],
        },
        "hard_constraint_candidates": {
            "locations": ["Shanghai"],
            "min_years": 5,
            "max_years": 10,
        },
        "scoring_rationale_candidate": "Prioritize core must-have fit.",
    }


def _grounding_draft_payload() -> dict[str, object]:
    return {
        "grounding_evidence_cards": [
            {
                "source_card_id": "role_alias.llm_agent_rag_engineering.backend_agent_engineer",
                "label": "agent engineer",
                "rationale": "title alias match",
                "evidence_type": "title_alias",
                "confidence": "high",
            }
        ],
        "frontier_seed_specifications": [
            {
                "operator_name": "must_have_alias",
                "seed_terms": ["agent engineer", "rag", "python"],
                "seed_rationale": "cover role anchor",
                "source_card_ids": [
                    "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
                ],
                "expected_coverage": ["Python backend", "LLM application"],
                "negative_terms": ["frontend"],
                "target_location": None,
            },
            {
                "operator_name": "strict_core",
                "seed_terms": ["retrieval engineer", "ranking", "python"],
                "seed_rationale": "cover retrieval branch",
                "source_card_ids": [
                    "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
                ],
                "expected_coverage": ["retrieval or ranking experience"],
                "negative_terms": [],
                "target_location": None,
            },
            {
                "operator_name": "domain_company",
                "seed_terms": ["workflow orchestration", "to-b", "python"],
                "seed_rationale": "cover business delivery",
                "source_card_ids": [
                    "role_alias.llm_agent_rag_engineering.backend_agent_engineer"
                ],
                "expected_coverage": ["workflow orchestration"],
                "negative_terms": [],
                "target_location": None,
            },
        ],
    }


def _candidate(candidate_id: str, *, search_text: str) -> RetrievedCandidate_t:
    return RetrievedCandidate_t(
        candidate_id=candidate_id,
        now_location="Shanghai",
        expected_location="Shanghai",
        years_of_experience_raw=6,
        education_summaries=["复旦大学 计算机 本科"],
        work_experience_summaries=[
            "TestCo | Python Engineer | Built retrieval ranking systems."
        ],
        project_names=["retrieval platform"],
        work_summaries=["python", "ranking"],
        search_text=search_text,
        raw_payload={"title": "Python Engineer", "workExperienceList": []},
    )


@dataclass
class FakeCTSClient:
    results: list[CTSFetchResult]
    seen_plans: list[object] = field(default_factory=list)

    async def search(self, plan, *, trace_id: str = "") -> CTSFetchResult:
        del trace_id
        self.seen_plans.append(plan)
        if not self.results:
            raise AssertionError("unexpected_cts_call")
        return self.results.pop(0)


@dataclass
class FakeRerankRequest:
    responses: list[RerankResponse]
    seen_requests: list[object] = field(default_factory=list)

    async def __call__(self, request):
        self.seen_requests.append(request)
        if not self.responses:
            raise AssertionError("unexpected_rerank_call")
        return self.responses.pop(0)


@dataclass
class SequentialTestModel:
    outputs: list[dict[str, object]]
    model_name: str = "test"

    @property
    def custom_output_args(self) -> dict[str, object]:
        if not self.outputs:
            raise AssertionError("unexpected_model_call")
        return self.outputs.pop(0)


def _runtime_assets(*, min_round_index: int) -> object:
    return replace(
        default_bootstrap_assets(),
        stop_guard_thresholds=StopGuardThresholds(min_round_index=min_round_index),
    )


def test_workflow_runtime_search_then_controller_stop_finalize() -> None:
    runtime = WorkflowRuntime(
        AppSettings(_env_file=None, mock_cts=True),
        assets=_runtime_assets(min_round_index=1),
        cts_client=FakeCTSClient(
            results=[
                CTSFetchResult(
                    request_payload={},
                    candidates=[_candidate("candidate-1", search_text="python ranking workflow")],
                    raw_candidate_count=1,
                    latency_ms=5,
                )
            ]
        ),
        rerank_request=FakeRerankRequest(
            responses=[
                RerankResponse(
                    model="test-reranker",
                    results=[
                        RerankResult(
                            id="candidate-1",
                            index=0,
                            score=2.0,
                            rank=1,
                        )
                    ],
                )
            ]
        ),
        requirement_extraction_model=TestModel(
            custom_output_args=_requirement_draft_payload()
        ),
        grounding_generation_model=TestModel(
            custom_output_args=_grounding_draft_payload()
        ),
        search_controller_decision_model=SequentialTestModel(
            outputs=[
                {
                    "action": "search_cts",
                    "selected_operator_name": "strict_core",
                    "operator_args": {"additional_terms": ["ranking"]},
                    "expected_gain_hypothesis": "Expand ranking coverage.",
                },
                {
                    "action": "stop",
                    "selected_operator_name": "strict_core",
                    "operator_args": {},
                    "expected_gain_hypothesis": "Enough evidence.",
                },
            ]
        ),
        branch_outcome_evaluation_model=TestModel(
            custom_output_args={
                "novelty_score": 0.8,
                "usefulness_score": 0.7,
                "branch_exhausted": False,
                "repair_operator_hint": "strict_core",
                "evaluation_notes": "Good expansion.",
            }
        ),
        search_run_finalization_model=TestModel(
            custom_output_args={"run_summary": "The shortlist is ready for review."}
        ),
    )

    result = asyncio.run(
        runtime.run_async(
            job_description="Senior Python / LLM Engineer",
            hiring_notes="Shanghai preferred",
        )
    )

    assert result.stop_reason == "controller_stop"
    assert result.final_shortlist_candidate_ids == ["candidate-1"]
    assert result.run_summary == "The shortlist is ready for review."


def test_workflow_runtime_stops_on_exhausted_low_gain() -> None:
    runtime = WorkflowRuntime(
        AppSettings(_env_file=None, mock_cts=True),
        assets=_runtime_assets(min_round_index=2),
        cts_client=FakeCTSClient(
            results=[
                CTSFetchResult(
                    request_payload={},
                    candidates=[],
                    raw_candidate_count=0,
                    latency_ms=5,
                )
            ]
        ),
        rerank_request=FakeRerankRequest(responses=[]),
        requirement_extraction_model=TestModel(
            custom_output_args=_requirement_draft_payload()
        ),
        grounding_generation_model=TestModel(
            custom_output_args=_grounding_draft_payload()
        ),
        search_controller_decision_model=TestModel(
            custom_output_args={
                "action": "search_cts",
                "selected_operator_name": "strict_core",
                "operator_args": {"additional_terms": ["ranking"]},
                "expected_gain_hypothesis": "Try one more search.",
            }
        ),
        branch_outcome_evaluation_model=TestModel(
            custom_output_args={
                "novelty_score": 0.1,
                "usefulness_score": 0.1,
                "branch_exhausted": False,
                "repair_operator_hint": "strict_core",
                "evaluation_notes": "No useful new fit.",
            }
        ),
        search_run_finalization_model=TestModel(
            custom_output_args={
                "run_summary": "The latest branch added too little value."
            }
        ),
    )

    result = asyncio.run(
        runtime.run_async(
            job_description="Senior Python / LLM Engineer",
            hiring_notes="Shanghai preferred",
        )
    )

    assert result.stop_reason == "exhausted_low_gain"
    assert result.final_shortlist_candidate_ids == []
    assert result.run_summary == "The latest branch added too little value."


def test_workflow_runtime_rejects_direct_stop_then_accepts_next_round() -> None:
    rerank = FakeRerankRequest(responses=[])
    runtime = WorkflowRuntime(
        AppSettings(_env_file=None, mock_cts=True),
        assets=_runtime_assets(min_round_index=1),
        cts_client=FakeCTSClient(results=[]),
        rerank_request=rerank,
        requirement_extraction_model=TestModel(
            custom_output_args=_requirement_draft_payload()
        ),
        grounding_generation_model=TestModel(
            custom_output_args=_grounding_draft_payload()
        ),
        search_controller_decision_model=TestModel(
            custom_output_args=[
                {
                    "action": "stop",
                    "selected_operator_name": "must_have_alias",
                    "operator_args": {},
                    "expected_gain_hypothesis": "Stop now.",
                },
                {
                    "action": "stop",
                    "selected_operator_name": "must_have_alias",
                    "operator_args": {},
                    "expected_gain_hypothesis": "Stop now.",
                },
            ]
        ),
        search_run_finalization_model=TestModel(
            custom_output_args={"run_summary": "Stopped after controller confirmation."}
        ),
    )

    result = asyncio.run(
        runtime.run_async(
            job_description="Senior Python / LLM Engineer",
            hiring_notes="Shanghai preferred",
        )
    )

    assert result.stop_reason == "controller_stop"
    assert result.final_shortlist_candidate_ids == []
    assert rerank.seen_requests == []
