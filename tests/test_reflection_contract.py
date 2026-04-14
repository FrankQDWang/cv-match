import pytest
from pydantic import ValidationError

from seektalent.models import ReflectionAdvice, ReflectionFilterAdvice, ReflectionKeywordAdvice


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
        ReflectionFilterAdvice(suggested_add_filter_fields=["unsupported_field"])
