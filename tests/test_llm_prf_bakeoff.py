from __future__ import annotations

from pathlib import Path

import pytest

from seektalent.candidate_feedback.llm_prf_bakeoff import (
    LLMPRFBakeoffResult,
    load_bakeoff_cases,
    main,
    score_llm_prf_bakeoff_results,
)


FIXTURE_PATH = Path("tests/fixtures/llm_prf_bakeoff/cases.jsonl")


def test_bakeoff_metrics_mark_blocker_for_accepted_non_extractive_phrase() -> None:
    result = LLMPRFBakeoffResult(
        case_id="case-1",
        language_bucket="english",
        accepted_expression="Invented Phrase",
        accepted_grounded=False,
        accepted_reject_reasons=[],
        fallback_reason=None,
        structured_output_failed=False,
        latency_ms=1200,
    )

    metrics = score_llm_prf_bakeoff_results([result])

    assert metrics["blocker_count"] == 1
    assert metrics["non_extractive_accepted_count"] == 1


def test_bakeoff_metrics_count_no_safe_expression_as_fallback_not_blocker() -> None:
    result = LLMPRFBakeoffResult(
        case_id="case-1",
        language_bucket="mixed",
        accepted_expression=None,
        accepted_grounded=False,
        accepted_reject_reasons=[],
        fallback_reason="no_safe_llm_prf_expression",
        structured_output_failed=False,
        latency_ms=900,
    )

    metrics = score_llm_prf_bakeoff_results([result])

    assert metrics["generic_fallback_rate"] == 1.0
    assert metrics["blocker_count"] == 0


def test_bakeoff_metrics_report_language_counts_and_latency_percentiles() -> None:
    results = [
        LLMPRFBakeoffResult(case_id="a", language_bucket="english", latency_ms=100),
        LLMPRFBakeoffResult(case_id="b", language_bucket="chinese", latency_ms=200, structured_output_failed=True),
        LLMPRFBakeoffResult(case_id="c", language_bucket="mixed", latency_ms=300, fallback_reason="timeout"),
    ]

    metrics = score_llm_prf_bakeoff_results(results)

    assert metrics["case_count"] == 3
    assert metrics["structured_output_failure_rate"] == pytest.approx(1 / 3)
    assert metrics["generic_fallback_rate"] == pytest.approx(1 / 3)
    assert metrics["latency_ms_p50"] == 200
    assert metrics["latency_ms_p95"] == 300
    assert metrics["language_bucket_counts"] == {"english": 1, "chinese": 1, "mixed": 1}


def test_load_bakeoff_cases_reads_checked_in_smoke_fixture() -> None:
    cases = load_bakeoff_cases(FIXTURE_PATH)

    assert [case.case_id for case in cases] == ["english_streaming", "chinese_algorithm", "mixed_llm_ops"]
    assert {case.language_bucket for case in cases} == {"english", "chinese", "mixed"}


def test_bakeoff_cli_requires_live_flag(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--cases", str(FIXTURE_PATH), "--output-dir", str(tmp_path)])

    assert "--live is required" in str(exc_info.value)
