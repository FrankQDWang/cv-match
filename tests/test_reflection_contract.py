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
)
from seektalent.reflection.critic import materialize_reflection_advice


def test_reflection_advice_requires_stop_reason_when_stopping() -> None:
    with pytest.raises(ValidationError):
        ReflectionAdvice(
            strategy_assessment="No more value.",
            quality_assessment="Top pool is already strong.",
            coverage_assessment="Coverage is sufficient.",
            keyword_advice=ReflectionKeywordAdvice(),
            filter_advice=ReflectionFilterAdvice(),
            suggest_stop=True,
            reflection_summary="Stop here.",
        )


def test_reflection_advice_rejects_stop_reason_when_continuing() -> None:
    with pytest.raises(ValidationError):
        ReflectionAdvice(
            strategy_assessment="Need another round.",
            quality_assessment="Top pool is not stable yet.",
            coverage_assessment="Coverage is still narrow.",
            keyword_advice=ReflectionKeywordAdvice(),
            filter_advice=ReflectionFilterAdvice(),
            suggest_stop=False,
            suggested_stop_reason="reflection_stop",
            reflection_summary="Continue.",
        )


def test_reflection_filter_advice_rejects_unknown_filter_fields() -> None:
    with pytest.raises(ValidationError):
        ReflectionFilterAdvice.model_validate({"suggested_add_filter_fields": ["unsupported_field"]})


def test_reflection_advice_draft_requires_stop_reason_when_stopping() -> None:
    with pytest.raises(ValidationError):
        ReflectionAdviceDraft(
            strategy_assessment="No more value.",
            quality_assessment="Top pool is already strong.",
            coverage_assessment="Coverage is sufficient.",
            keyword_advice=ReflectionKeywordAdviceDraft(),
            filter_advice=ReflectionFilterAdviceDraft(),
            suggest_stop=True,
        )


def test_materialized_reflection_prose_mentions_only_structured_activate_terms() -> None:
    context = SimpleNamespace(round_no=3, search_observation=SimpleNamespace(unique_new_count=0))
    advice = materialize_reflection_advice(
        context=cast(Any, context),
        draft=ReflectionAdviceDraft(
            strategy_assessment="Need broader framework coverage.",
            quality_assessment="Top pool is narrow.",
            coverage_assessment="Coverage collapsed.",
            keyword_advice=ReflectionKeywordAdviceDraft(
                suggested_activate_terms=["AutoGen"],
                suggested_deprioritize_terms=["LangChain"],
            ),
            filter_advice=ReflectionFilterAdviceDraft(suggested_drop_filter_fields=["position"]),
        ),
    )

    assert "AutoGen" in advice.keyword_advice.critique
    assert "AutoGen" in advice.reflection_summary
    assert "LangChain" in advice.reflection_summary
    assert "position" in advice.reflection_summary


def test_materialized_reflection_prose_does_not_invent_terms() -> None:
    context = SimpleNamespace(round_no=2, search_observation=SimpleNamespace(unique_new_count=1))
    advice = materialize_reflection_advice(
        context=cast(Any, context),
        draft=ReflectionAdviceDraft(
            strategy_assessment="Direction is stable.",
            quality_assessment="Pool quality is mixed.",
            coverage_assessment="Coverage is acceptable.",
            keyword_advice=ReflectionKeywordAdviceDraft(),
            filter_advice=ReflectionFilterAdviceDraft(),
        ),
    )

    assert advice.keyword_advice.critique == "No keyword changes."
    assert "AutoGen" not in advice.reflection_summary
    assert advice.reflection_summary == "Round 2 yielded 1 new candidate. Keywords: No keyword changes. Filters: no filter changes. Continue."
