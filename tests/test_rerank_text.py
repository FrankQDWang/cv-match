from __future__ import annotations

from seektalent.models import HardConstraints, RequirementPreferences, RequirementSheet
from seektalent.rerank_text import build_rerank_query_text


def test_build_rerank_query_text_renders_natural_language_query() -> None:
    requirement_sheet = RequirementSheet(
        role_title="Senior Python / LLM Engineer",
        role_summary="Build Python, LLM, and retrieval systems.",
        must_have_capabilities=[
            "Python backend",
            "LLM application",
            "retrieval pipeline",
        ],
        preferred_capabilities=["workflow orchestration", "tool calling"],
        exclusion_signals=[],
        preferences=RequirementPreferences(),
        hard_constraints=HardConstraints(
            locations=["上海"],
            min_years=5,
            max_years=10,
        ),
        scoring_rationale="must-have 优先，偏好次之。",
    )

    assert build_rerank_query_text(requirement_sheet) == (
        "Hiring for Senior Python / LLM Engineer. "
        "Must have Python backend, LLM application, retrieval pipeline. "
        "Location: 上海. "
        "Minimum 5 years of experience. "
        "Maximum 10 years of experience. "
        "Preferred workflow orchestration, tool calling."
    )
