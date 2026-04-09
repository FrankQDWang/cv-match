from __future__ import annotations

import asyncio
from dataclasses import replace

from pydantic_ai.models.test import TestModel

from seektalent import AppSettings, __version__, run_match, run_match_async
from seektalent.bootstrap_assets import default_bootstrap_assets
from seektalent.models import StopGuardThresholds


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
        "exclusion_signal_candidates": [],
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
                "negative_terms": [],
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


def _active_assets():
    return replace(
        default_bootstrap_assets(),
        stop_guard_thresholds=StopGuardThresholds(min_round_index=1),
    )


def test_run_match_returns_search_run_result() -> None:
    result = run_match(
        job_description="Senior Python / LLM Engineer",
        hiring_notes="Shanghai preferred",
        settings=AppSettings(_env_file=None, mock_cts=True),
        env_file=None,
        assets=_active_assets(),
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
                    "expected_gain_hypothesis": "Stop.",
                },
                {
                    "action": "stop",
                    "selected_operator_name": "must_have_alias",
                    "operator_args": {},
                    "expected_gain_hypothesis": "Stop.",
                },
            ]
        ),
        search_run_finalization_model=TestModel(
            custom_output_args={"run_summary": "Controller stop accepted."}
        ),
    )

    assert result.stop_reason == "controller_stop"
    assert result.final_shortlist_candidate_ids == []
    assert result.run_summary == "Controller stop accepted."


def test_run_match_async_returns_search_run_result() -> None:
    result = asyncio.run(
        run_match_async(
            job_description="Senior Python / LLM Engineer",
            hiring_notes="Shanghai preferred",
            settings=AppSettings(_env_file=None, mock_cts=True),
            env_file=None,
            assets=_active_assets(),
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
                        "expected_gain_hypothesis": "Stop.",
                    },
                    {
                        "action": "stop",
                        "selected_operator_name": "must_have_alias",
                        "operator_args": {},
                        "expected_gain_hypothesis": "Stop.",
                    },
                ]
            ),
            search_run_finalization_model=TestModel(
                custom_output_args={"run_summary": "Controller stop accepted."}
            ),
        )
    )

    assert result.stop_reason == "controller_stop"
    assert result.final_shortlist_candidate_ids == []


def test_top_level_exports_remain_available() -> None:
    settings = AppSettings(_env_file=None, mock_cts=True)
    assert settings.mock_cts is True
    assert __version__ == "0.3.0a1"
