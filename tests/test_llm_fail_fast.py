from __future__ import annotations

from pathlib import Path

import pytest

from cv_match.config import AppSettings
from cv_match.controller.react_controller import ReActController
from cv_match.finalize.finalizer import Finalizer
from cv_match.models import (
    ControllerContext,
    HardConstraintSlots,
    InputTruth,
    LocationExecutionPlan,
    QueryTermCandidate,
    ReflectionContext,
    RequirementSheet,
    RoundRetrievalPlan,
    SearchObservation,
)
from cv_match.prompting import LoadedPrompt
from cv_match.requirements import RequirementExtractor
from cv_match.reflection.critic import ReflectionCritic


def _prompt(name: str) -> LoadedPrompt:
    return LoadedPrompt(name=name, path=Path(f"{name}.md"), content=f"{name} prompt", sha256="hash")


def _settings(monkeypatch: pytest.MonkeyPatch) -> AppSettings:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    return AppSettings(_env_file=None)


def _requirement_sheet() -> RequirementSheet:
    return RequirementSheet(
        role_title="Senior Python Engineer",
        role_summary="Build resume matching workflows.",
        must_have_capabilities=["python"],
        preferred_capabilities=["trace"],
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


def _controller_context() -> ControllerContext:
    requirement_sheet = _requirement_sheet()
    return ControllerContext(
        full_jd="jd",
        full_notes="notes",
        requirement_sheet=requirement_sheet,
        round_no=1,
        min_rounds=1,
        max_rounds=3,
        target_new=10,
        query_term_pool=requirement_sheet.initial_query_term_pool,
    )


def _reflection_context() -> ReflectionContext:
    requirement_sheet = _requirement_sheet()
    retrieval_plan = RoundRetrievalPlan(
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
        rationale="test retrieval plan",
    )
    search_observation = SearchObservation(
        round_no=1,
        requested_count=10,
        raw_candidate_count=0,
        unique_new_count=0,
        shortage_count=10,
        fetch_attempt_count=1,
        exhausted_reason="cts_exhausted",
        new_resume_ids=[],
        new_candidate_summaries=[],
        adapter_notes=[],
    )
    return ReflectionContext(
        round_no=1,
        full_jd="jd",
        full_notes="notes",
        requirement_sheet=requirement_sheet,
        current_retrieval_plan=retrieval_plan,
        search_observation=search_observation,
    )


def test_controller_decide_raises_live_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = ReActController(_settings(monkeypatch), _prompt("controller"))

    async def boom(*, context):  # noqa: ARG001
        raise RuntimeError("controller boom")

    controller._decide_live = boom  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="controller boom"):
        controller.decide(context=_controller_context())


def test_requirement_extractor_raises_live_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    extractor = RequirementExtractor(_settings(monkeypatch), _prompt("requirements"))

    async def boom(*, input_truth):  # noqa: ARG001
        raise RuntimeError("requirements boom")

    extractor._extract_live = boom  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="requirements boom"):
        extractor.extract(
            input_truth=InputTruth(
                jd="jd",
                notes="notes",
                jd_sha256="jd-hash",
                notes_sha256="notes-hash",
            )
        )


def test_reflection_reflect_raises_live_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    critic = ReflectionCritic(_settings(monkeypatch), _prompt("reflection"))

    async def boom(*, context):  # noqa: ARG001
        raise RuntimeError("reflection boom")

    critic._reflect_live = boom  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="reflection boom"):
        critic.reflect(context=_reflection_context())


def test_finalizer_uses_live_path_and_raises_for_empty_ranked_list(monkeypatch: pytest.MonkeyPatch) -> None:
    finalizer = Finalizer(_settings(monkeypatch), _prompt("finalize"))

    async def boom(**kwargs):  # noqa: ARG001
        raise RuntimeError("finalizer boom")

    finalizer._finalize_live = boom  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="finalizer boom"):
        finalizer.finalize(
            run_id="run-1",
            run_dir="/tmp/run-1",
            rounds_executed=1,
            stop_reason="controller_stop",
            ranked_candidates=[],
        )
