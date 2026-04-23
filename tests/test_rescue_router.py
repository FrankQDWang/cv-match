from __future__ import annotations

from seektalent.models import StopGuidance
from seektalent.runtime.rescue_router import RescueInputs, choose_rescue_lane


def _guidance(status: str = "broaden_required", *, top_pool_strength: str = "weak") -> StopGuidance:
    return StopGuidance(
        can_stop=False,
        reason="top pool weak",
        top_pool_strength=top_pool_strength,
        quality_gate_status=status,
    )


def test_reserve_broaden_is_preferred_when_reserve_family_is_untried() -> None:
    decision = choose_rescue_lane(
        RescueInputs(
            stop_guidance=_guidance(),
            has_untried_reserve_family=True,
            has_feedback_seed_resumes=True,
            candidate_feedback_enabled=True,
            candidate_feedback_attempted=False,
            company_discovery_enabled=True,
            company_discovery_attempted=False,
            company_discovery_useful=True,
            anchor_only_broaden_attempted=False,
        )
    )

    assert decision.selected_lane == "reserve_broaden"


def test_candidate_feedback_is_selected_before_company_discovery() -> None:
    decision = choose_rescue_lane(
        RescueInputs(
            stop_guidance=_guidance(),
            has_untried_reserve_family=False,
            has_feedback_seed_resumes=True,
            candidate_feedback_enabled=True,
            candidate_feedback_attempted=False,
            company_discovery_enabled=True,
            company_discovery_attempted=False,
            company_discovery_useful=True,
            anchor_only_broaden_attempted=False,
        )
    )

    assert decision.selected_lane == "candidate_feedback"


def test_web_company_discovery_is_selected_before_anchor_only() -> None:
    decision = choose_rescue_lane(
        RescueInputs(
            stop_guidance=_guidance(),
            has_untried_reserve_family=False,
            has_feedback_seed_resumes=False,
            candidate_feedback_enabled=True,
            candidate_feedback_attempted=False,
            company_discovery_enabled=True,
            company_discovery_attempted=False,
            company_discovery_useful=True,
            anchor_only_broaden_attempted=False,
        )
    )

    assert decision.selected_lane == "web_company_discovery"


def test_anchor_only_is_selected_after_other_lanes_are_unavailable_or_attempted() -> None:
    decision = choose_rescue_lane(
        RescueInputs(
            stop_guidance=_guidance(),
            has_untried_reserve_family=False,
            has_feedback_seed_resumes=False,
            candidate_feedback_enabled=False,
            candidate_feedback_attempted=True,
            company_discovery_enabled=False,
            company_discovery_attempted=True,
            company_discovery_useful=False,
            anchor_only_broaden_attempted=False,
        )
    )

    assert decision.selected_lane == "anchor_only"


def test_allow_stop_is_selected_outside_rescue_statuses() -> None:
    decision = choose_rescue_lane(
        RescueInputs(
            stop_guidance=_guidance(status="pass"),
            has_untried_reserve_family=True,
            has_feedback_seed_resumes=True,
            candidate_feedback_enabled=True,
            candidate_feedback_attempted=False,
            company_discovery_enabled=True,
            company_discovery_attempted=False,
            company_discovery_useful=True,
            anchor_only_broaden_attempted=False,
        )
    )

    assert decision.selected_lane == "allow_stop"
