from __future__ import annotations

from seektalent.models import RuntimeSearchBudget
from seektalent.runtime_budget import (
    build_runtime_budget_state,
    resolve_runtime_search_budget,
)


def test_resolve_runtime_search_budget_clamps_requested_value() -> None:
    low = resolve_runtime_search_budget(RuntimeSearchBudget(initial_round_budget=5), 3)
    high = resolve_runtime_search_budget(RuntimeSearchBudget(initial_round_budget=5), 20)

    assert low.initial_round_budget == 5
    assert high.initial_round_budget == 12


def test_build_runtime_budget_state_marks_near_budget_end_from_used_ratio() -> None:
    early = build_runtime_budget_state(
        initial_round_budget=10,
        runtime_round_index=1,
        remaining_budget=9,
    )
    late = build_runtime_budget_state(
        initial_round_budget=10,
        runtime_round_index=8,
        remaining_budget=2,
    )

    assert early.used_ratio == 0.1
    assert early.near_budget_end is False
    assert late.used_ratio == 0.8
    assert late.remaining_ratio == 0.2
    assert late.near_budget_end is True
