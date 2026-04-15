from pathlib import Path

import pytest
from pydantic_ai.exceptions import ModelRetry

from seektalent.config import AppSettings
from seektalent.finalize.finalizer import Finalizer
from seektalent.models import FinalCandidate, FinalResult, FinalizeContext, ScoredCandidate
from seektalent.prompting import LoadedPrompt


def _scored_candidate(resume_id: str, *, source_round: int, score: int) -> ScoredCandidate:
    return ScoredCandidate(
        resume_id=resume_id,
        fit_bucket="fit",
        overall_score=score,
        must_have_match_score=score,
        preferred_match_score=70,
        risk_score=10,
        risk_flags=[],
        reasoning_summary="Strong role match.",
        evidence=["python"],
        confidence="high",
        matched_must_haves=["python"],
        missing_must_haves=[],
        matched_preferences=["trace"],
        negative_signals=[],
        strengths=["Relevant backend work."],
        weaknesses=[],
        source_round=source_round,
    )


def _candidate(resume_id: str, *, rank: int, source_round: int) -> FinalCandidate:
    return FinalCandidate(
        resume_id=resume_id,
        rank=rank,
        final_score=90,
        fit_bucket="fit",
        match_summary="Strong backend match.",
        strengths=["Relevant backend work."],
        weaknesses=[],
        matched_must_haves=["python"],
        matched_preferences=["trace"],
        risk_flags=[],
        why_selected="Strong role fit.",
        source_round=source_round,
    )


def _validator(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    finalizer = Finalizer(
        AppSettings(_env_file=None),
        LoadedPrompt(name="finalize", path=Path("finalize.md"), content="finalize prompt", sha256="hash"),
    )
    return finalizer._get_agent()._output_validators[0].function


def _deps() -> FinalizeContext:
    return FinalizeContext(
        run_id="run-1",
        run_dir="/tmp/run-1",
        rounds_executed=2,
        stop_reason="reflection_stop",
        top_candidates=[
            _scored_candidate("r-1", source_round=1, score=95),
            _scored_candidate("r-2", source_round=2, score=90),
            _scored_candidate("r-3", source_round=2, score=85),
        ],
    )


def test_finalizer_output_validator_rejects_duplicate_resume_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _validator(monkeypatch)
    output = FinalResult(
        run_id="run-1",
        run_dir="/tmp/run-1",
        rounds_executed=2,
        stop_reason="reflection_stop",
        summary="Returned 2 candidates.",
        candidates=[
            _candidate("r-1", rank=1, source_round=1),
            _candidate("r-1", rank=2, source_round=1),
        ],
    )

    with pytest.raises(ModelRetry, match="Duplicate"):
        validator(type("Ctx", (), {"deps": _deps()})(), output)


def test_finalizer_output_validator_rejects_unknown_resume_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _validator(monkeypatch)
    output = FinalResult(
        run_id="run-1",
        run_dir="/tmp/run-1",
        rounds_executed=2,
        stop_reason="reflection_stop",
        summary="Returned 1 candidate.",
        candidates=[_candidate("r-9", rank=1, source_round=1)],
    )

    with pytest.raises(ModelRetry, match="Unknown resume_id"):
        validator(type("Ctx", (), {"deps": _deps()})(), output)


def test_finalizer_output_validator_rejects_non_contiguous_ranks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _validator(monkeypatch)
    output = FinalResult(
        run_id="run-1",
        run_dir="/tmp/run-1",
        rounds_executed=2,
        stop_reason="reflection_stop",
        summary="Returned 2 candidates.",
        candidates=[
            _candidate("r-1", rank=1, source_round=1),
            _candidate("r-2", rank=3, source_round=2),
        ],
    )

    with pytest.raises(ModelRetry, match="contiguous"):
        validator(type("Ctx", (), {"deps": _deps()})(), output)


def test_finalizer_output_validator_rejects_incomplete_shortlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _validator(monkeypatch)
    output = FinalResult(
        run_id="run-1",
        run_dir="/tmp/run-1",
        rounds_executed=2,
        stop_reason="reflection_stop",
        summary="Returned 2 candidates.",
        candidates=[
            _candidate("r-1", rank=1, source_round=1),
            _candidate("r-2", rank=2, source_round=2),
        ],
    )

    with pytest.raises(ModelRetry, match="include every runtime-ranked candidate"):
        validator(type("Ctx", (), {"deps": _deps()})(), output)


def test_finalizer_output_validator_rejects_source_round_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _validator(monkeypatch)
    output = FinalResult(
        run_id="run-1",
        run_dir="/tmp/run-1",
        rounds_executed=2,
        stop_reason="reflection_stop",
        summary="Returned 1 candidate.",
        candidates=[_candidate("r-2", rank=1, source_round=1)],
    )

    with pytest.raises(ModelRetry, match="source_round"):
        validator(type("Ctx", (), {"deps": _deps()})(), output)


def test_finalizer_output_validator_accepts_complete_runtime_shortlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _validator(monkeypatch)
    output = FinalResult(
        run_id="run-1",
        run_dir="/tmp/run-1",
        rounds_executed=2,
        stop_reason="reflection_stop",
        summary="Returned 3 candidates.",
        candidates=[
            _candidate("r-1", rank=1, source_round=1),
            _candidate("r-2", rank=2, source_round=2),
            _candidate("r-3", rank=3, source_round=2),
        ],
    )

    validated = validator(type("Ctx", (), {"deps": _deps()})(), output)

    assert validated == output
