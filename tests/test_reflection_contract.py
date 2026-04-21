from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from pydantic import ValidationError

from seektalent.models import (
    ReflectionAdvice,
    ReflectionAdviceDraft,
    ReflectionFilterAdvice,
    ReflectionFilterAdviceDraft,
    ReflectionKeywordAdvice,
    ReflectionKeywordAdviceDraft,
    QueryTermCandidate,
)
from seektalent.reflection.critic import materialize_reflection_advice


def _context(
    *,
    round_no: int,
    unique_new_count: int,
    query_term_pool: list[QueryTermCandidate] | None = None,
    sent_query_terms: list[list[str]] | None = None,
    top_candidates: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        round_no=round_no,
        search_observation=SimpleNamespace(unique_new_count=unique_new_count),
        requirement_sheet=SimpleNamespace(initial_query_term_pool=query_term_pool or []),
        sent_query_history=[
            SimpleNamespace(query_terms=query_terms)
            for query_terms in (sent_query_terms or [])
        ],
        top_candidates=top_candidates or [],
    )


def _scored_candidate(
    *,
    fit_bucket: str = "fit",
    overall_score: int = 80,
    must_have_match_score: int = 70,
    risk_score: int = 20,
) -> SimpleNamespace:
    return SimpleNamespace(
        fit_bucket=fit_bucket,
        overall_score=overall_score,
        must_have_match_score=must_have_match_score,
        risk_score=risk_score,
    )


def test_reflection_advice_requires_stop_reason_when_stopping() -> None:
    with pytest.raises(ValidationError):
        ReflectionAdvice(
            keyword_advice=ReflectionKeywordAdvice(),
            filter_advice=ReflectionFilterAdvice(),
            suggest_stop=True,
            reflection_summary="Stop here.",
        )


def test_reflection_advice_rejects_stop_reason_when_continuing() -> None:
    with pytest.raises(ValidationError):
        ReflectionAdvice(
            keyword_advice=ReflectionKeywordAdvice(),
            filter_advice=ReflectionFilterAdvice(),
            suggest_stop=False,
            suggested_stop_reason="reflection_stop",
            reflection_summary="Continue.",
        )


def test_reflection_filter_advice_rejects_unknown_filter_fields() -> None:
    with pytest.raises(ValidationError):
        ReflectionFilterAdvice.model_validate({"suggested_add_filter_fields": ["unsupported_field"]})


def test_reflection_advice_rejects_removed_prose_fields() -> None:
    with pytest.raises(ValidationError):
        ReflectionAdvice.model_validate(
            {
                "strategy_assessment": "No more value.",
                "quality_assessment": "Top pool is strong.",
                "coverage_assessment": "Coverage is enough.",
                "keyword_advice": {},
                "filter_advice": {},
                "suggest_stop": False,
                "reflection_summary": "Continue.",
            }
        )


def test_reflection_keyword_advice_rejects_persisted_critique() -> None:
    with pytest.raises(ValidationError):
        ReflectionKeywordAdvice.model_validate({"critique": "Keep one term."})


def test_reflection_filter_advice_rejects_persisted_critique() -> None:
    with pytest.raises(ValidationError):
        ReflectionFilterAdvice.model_validate({"critique": "Keep position."})


def test_reflection_prompt_requires_untried_term_stop_discipline() -> None:
    prompt = Path("src/seektalent/prompts/reflection.md").read_text(encoding="utf-8")
    assert "`suggest_stop` is advisory only" in prompt
    assert "Do not dismiss unused concrete terms as unlikely without first trying them" in prompt


def test_reflection_advice_draft_requires_stop_reason_when_stopping() -> None:
    with pytest.raises(ValidationError):
        ReflectionAdviceDraft(
            keyword_advice=ReflectionKeywordAdviceDraft(),
            filter_advice=ReflectionFilterAdviceDraft(),
            suggest_stop=True,
            reflection_rationale="Top pool is good enough to stop.",
        )


def test_materialized_reflection_preserves_rationale_for_trace() -> None:
    context = _context(round_no=2, unique_new_count=10)
    advice = materialize_reflection_advice(
        context=cast(Any, context),
        draft=ReflectionAdviceDraft(
            keyword_advice=ReflectionKeywordAdviceDraft(suggested_activate_terms=["LangChain"]),
            filter_advice=ReflectionFilterAdviceDraft(),
            suggest_stop=False,
            reflection_rationale=(
                "Round 1 produced several plausible AI Agent candidates, but coverage is still narrow. "
                "Trying LangChain next should test the highest-signal unused framework term."
            ),
        ),
    )

    assert advice.reflection_rationale.startswith("Round 1 produced several plausible")
    assert "LangChain next" in advice.reflection_rationale


def test_materialized_reflection_prose_mentions_only_structured_activate_terms() -> None:
    context = _context(round_no=3, unique_new_count=0)
    advice = materialize_reflection_advice(
        context=cast(Any, context),
        draft=ReflectionAdviceDraft(
            keyword_advice=ReflectionKeywordAdviceDraft(
                suggested_activate_terms=["AutoGen"],
                suggested_deprioritize_terms=["LangChain"],
            ),
            filter_advice=ReflectionFilterAdviceDraft(suggested_drop_filter_fields=["position"]),
            suggest_stop=False,
            reflection_rationale="The search returned no new candidates, so adjust terms and remove stale filters.",
        ),
    )

    assert "AutoGen" in advice.reflection_summary
    assert "LangChain" in advice.reflection_summary
    assert "position" in advice.reflection_summary


def test_materialized_reflection_prose_does_not_invent_terms() -> None:
    context = _context(round_no=2, unique_new_count=1)
    advice = materialize_reflection_advice(
        context=cast(Any, context),
        draft=ReflectionAdviceDraft(
            keyword_advice=ReflectionKeywordAdviceDraft(),
            filter_advice=ReflectionFilterAdviceDraft(),
            suggest_stop=False,
            reflection_rationale="One new candidate is not enough evidence to change the plan.",
        ),
    )

    assert "AutoGen" not in advice.reflection_summary
    assert advice.reflection_summary == "Round 2 yielded 1 new candidate. Keywords: No keyword changes. Filters: no filter changes. Continue."


def test_materialized_reflection_forces_continue_when_untried_admitted_terms_remain() -> None:
    context = _context(
        round_no=3,
        unique_new_count=7,
        query_term_pool=[
            QueryTermCandidate(
                term="Flink",
                source="job_title",
                category="role_anchor",
                priority=1,
                evidence="Job title",
                first_added_round=0,
            ),
            QueryTermCandidate(
                term="Paimon",
                source="jd",
                category="tooling",
                priority=2,
                evidence="JD body",
                first_added_round=0,
            ),
        ],
        sent_query_terms=[["Flink"]],
        top_candidates=[_scored_candidate() for _ in range(6)],
    )

    advice = materialize_reflection_advice(
        context=cast(Any, context),
        draft=ReflectionAdviceDraft(
            keyword_advice=ReflectionKeywordAdviceDraft(suggested_keep_terms=["Flink"]),
            filter_advice=ReflectionFilterAdviceDraft(),
            suggest_stop=True,
            suggested_stop_reason="Search is saturated.",
            reflection_rationale="The pool is not yet strong enough and one admitted term remains untried.",
        ),
    )

    assert advice.suggest_stop is False
    assert advice.suggested_stop_reason is None
    assert "Paimon" in advice.reflection_summary
    assert "Continue: untried admitted reserve terms remain" in advice.reflection_summary


def test_materialized_reflection_allows_stop_when_top_pool_is_strong() -> None:
    context = _context(
        round_no=3,
        unique_new_count=7,
        query_term_pool=[
            QueryTermCandidate(
                term="Flink",
                source="job_title",
                category="role_anchor",
                priority=1,
                evidence="Job title",
                first_added_round=0,
            ),
            QueryTermCandidate(
                term="Paimon",
                source="jd",
                category="tooling",
                priority=2,
                evidence="JD body",
                first_added_round=0,
            ),
        ],
        sent_query_terms=[["Flink"]],
        top_candidates=[
            *[_scored_candidate() for _ in range(5)],
            *[_scored_candidate(overall_score=70, must_have_match_score=65) for _ in range(5)],
        ],
    )

    advice = materialize_reflection_advice(
        context=cast(Any, context),
        draft=ReflectionAdviceDraft(
            keyword_advice=ReflectionKeywordAdviceDraft(suggested_keep_terms=["Flink"]),
            filter_advice=ReflectionFilterAdviceDraft(),
            suggest_stop=True,
            suggested_stop_reason="Search is saturated.",
            reflection_rationale="The top pool is strong enough and the remaining term is unlikely to change the result.",
        ),
    )

    assert advice.suggest_stop is True
    assert advice.suggested_stop_reason == "Search is saturated."
