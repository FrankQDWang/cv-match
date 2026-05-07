from __future__ import annotations

from seektalent.providers.liepin.policy import LiepinCardCandidate, build_detail_open_plan


def test_already_opened_stable_provider_id_is_skipped() -> None:
    plan = build_detail_open_plan(
        candidates=[
            LiepinCardCandidate(
                candidate_id="candidate-1",
                stable_provider_id="stable-1",
                weak_fingerprint=None,
                card_value_score=0.9,
            )
        ],
        already_opened_provider_ids={"stable-1"},
        daily_detail_budget=3,
        consumed_detail_budget=0,
    )

    assert plan.decisions[0].action == "card_only"
    assert plan.decisions[0].reason == "stable_provider_id_already_opened"


def test_weak_fingerprints_do_not_hard_suppress_duplicates() -> None:
    plan = build_detail_open_plan(
        candidates=[
            LiepinCardCandidate(
                candidate_id="candidate-1",
                stable_provider_id=None,
                weak_fingerprint="same-name-company",
                card_value_score=0.9,
            )
        ],
        already_opened_provider_ids=set(),
        already_seen_weak_fingerprints={"same-name-company"},
        daily_detail_budget=3,
        consumed_detail_budget=0,
    )

    assert plan.decisions[0].action == "open_detail"
    assert plan.decisions[0].reason == "detail_budget_available"


def test_low_card_value_candidates_are_skipped_before_budget_is_spent() -> None:
    plan = build_detail_open_plan(
        candidates=[
            LiepinCardCandidate(
                candidate_id="low-value",
                stable_provider_id="stable-low",
                weak_fingerprint=None,
                card_value_score=0.1,
            ),
            LiepinCardCandidate(
                candidate_id="high-value",
                stable_provider_id="stable-high",
                weak_fingerprint=None,
                card_value_score=0.9,
            ),
        ],
        already_opened_provider_ids=set(),
        daily_detail_budget=1,
        consumed_detail_budget=0,
        min_card_value_score=0.5,
    )

    assert [(decision.candidate_id, decision.action, decision.reason) for decision in plan.decisions] == [
        ("low-value", "card_only", "low_card_value"),
        ("high-value", "open_detail", "detail_budget_available"),
    ]


def test_budget_exhaustion_degrades_to_card_only_candidates() -> None:
    plan = build_detail_open_plan(
        candidates=[
            LiepinCardCandidate(
                candidate_id="candidate-1",
                stable_provider_id="stable-1",
                weak_fingerprint=None,
                card_value_score=0.9,
            )
        ],
        already_opened_provider_ids=set(),
        daily_detail_budget=1,
        consumed_detail_budget=1,
    )

    assert plan.decisions[0].action == "card_only"
    assert plan.decisions[0].reason == "detail_budget_exhausted"


def test_detail_plan_emits_artifact_ready_reason_for_every_candidate() -> None:
    plan = build_detail_open_plan(
        candidates=[
            LiepinCardCandidate(
                candidate_id="opened",
                stable_provider_id="stable-opened",
                weak_fingerprint=None,
                card_value_score=0.9,
            ),
            LiepinCardCandidate(
                candidate_id="skipped",
                stable_provider_id="stable-skipped",
                weak_fingerprint=None,
                card_value_score=0.1,
            ),
        ],
        already_opened_provider_ids=set(),
        daily_detail_budget=2,
        consumed_detail_budget=0,
        min_card_value_score=0.5,
    )

    assert [decision.reason for decision in plan.decisions] == [
        "detail_budget_available",
        "low_card_value",
    ]
    for decision in plan.decisions:
        assert decision.artifact_reason == {
            "candidate_id": decision.candidate_id,
            "action": decision.action,
            "reason": decision.reason,
        }
