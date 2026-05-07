from __future__ import annotations

from pathlib import Path

import pytest

from seektalent.providers.liepin.store import LiepinStore


TENANT = "tenant-a"
WORKSPACE = "workspace-a"
ACTOR = "actor-a"
ACCOUNT = "account-hash-a"


def test_reserve_detail_attempt_is_idempotent_and_persists_day_keys(tmp_path: Path) -> None:
    store = _store(tmp_path)

    first = store.reserve_detail_attempt(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        provider_account_hash=ACCOUNT,
        candidate_provider_id="candidate-1",
        budget_date="2026-05-07",
        provider_day_key="liepin:account-hash-a:2026-05-07",
        timezone="Asia/Shanghai",
        idempotency_key="open:candidate-1",
    )
    second = store.reserve_detail_attempt(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        provider_account_hash=ACCOUNT,
        candidate_provider_id="candidate-1",
        budget_date="2026-05-07",
        provider_day_key="liepin:account-hash-a:2026-05-07",
        timezone="Asia/Shanghai",
        idempotency_key="open:candidate-1",
    )

    assert second == first
    assert first.state == "approved_not_started"
    assert first.consumption_state == "not_consumed"
    assert first.budget_date == "2026-05-07"
    assert first.provider_day_key == "liepin:account-hash-a:2026-05-07"
    assert first.timezone == "Asia/Shanghai"


def test_consumed_count_resets_by_provider_day_and_counts_uncertain_consumption(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _complete(store, "candidate-1", "2026-05-07", "liepin:account-hash-a:2026-05-07", "consumed")
    _complete(store, "candidate-2", "2026-05-07", "liepin:account-hash-a:2026-05-07", "possibly_consumed")
    _complete(store, "candidate-3", "2026-05-07", "liepin:account-hash-a:2026-05-07", "unknown")
    _complete(store, "candidate-4", "2026-05-08", "liepin:account-hash-a:2026-05-08", "consumed")

    assert (
        store.count_detail_budget_consumed(
            tenant_id=TENANT,
            workspace_id=WORKSPACE,
            actor_id=ACTOR,
            provider_account_hash=ACCOUNT,
            provider_day_key="liepin:account-hash-a:2026-05-07",
        )
        == 3
    )
    assert (
        store.count_detail_budget_consumed(
            tenant_id=TENANT,
            workspace_id=WORKSPACE,
            actor_id=ACTOR,
            provider_account_hash=ACCOUNT,
            provider_day_key="liepin:account-hash-a:2026-05-08",
        )
        == 1
    )


def test_duplicate_worker_response_is_applied_once(tmp_path: Path) -> None:
    store = _store(tmp_path)
    attempt = _reserve(store, "candidate-1")
    store.transition_detail_attempt(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        attempt_id=attempt.attempt_id,
        state="started",
        consumption_state="not_consumed",
        worker_command_id="cmd-1",
    )

    completed = store.apply_detail_worker_response(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        attempt_id=attempt.attempt_id,
        worker_response_id="worker-response-1",
        state="completed",
        consumption_state="consumed",
        worker_command_id="cmd-1",
        raw_evidence_ref="artifact:detail-1",
    )
    duplicate = store.apply_detail_worker_response(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        attempt_id=attempt.attempt_id,
        worker_response_id="worker-response-1",
        state="failed_after_possible_consumption",
        consumption_state="possibly_consumed",
        worker_command_id="cmd-1",
        raw_evidence_ref="artifact:conflicting-duplicate",
    )

    assert duplicate == completed
    assert duplicate.state == "completed"
    assert duplicate.started_at is not None
    assert duplicate.completed_at is not None
    assert duplicate.worker_command_id == "cmd-1"
    assert duplicate.raw_evidence_ref == "artifact:detail-1"
    assert (
        store.count_detail_budget_consumed(
            tenant_id=TENANT,
            workspace_id=WORKSPACE,
            actor_id=ACTOR,
            provider_account_hash=ACCOUNT,
            provider_day_key="liepin:account-hash-a:2026-05-07",
        )
        == 1
    )


def test_blocked_risk_control_records_evidence_without_completion(tmp_path: Path) -> None:
    store = _store(tmp_path)
    attempt = _reserve(store, "candidate-risk")
    store.transition_detail_attempt(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        attempt_id=attempt.attempt_id,
        state="started",
        consumption_state="not_consumed",
        worker_command_id="cmd-risk",
    )

    blocked = store.transition_detail_attempt(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        attempt_id=attempt.attempt_id,
        state="blocked_by_risk_control",
        consumption_state="not_consumed",
        raw_evidence_ref="artifact:risk-control",
    )

    assert blocked.state == "blocked_by_risk_control"
    assert blocked.worker_command_id == "cmd-risk"
    assert blocked.completed_at is None
    assert blocked.raw_evidence_ref == "artifact:risk-control"


def test_failed_before_consumption_does_not_consume_budget(tmp_path: Path) -> None:
    store = _store(tmp_path)
    attempt = _reserve(store, "candidate-before")

    failed = store.transition_detail_attempt(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        attempt_id=attempt.attempt_id,
        state="failed_before_consumption",
        consumption_state="not_consumed",
        raw_evidence_ref="artifact:navigation-failed",
    )

    assert failed.state == "failed_before_consumption"
    assert failed.consumption_state == "not_consumed"
    assert (
        store.count_detail_budget_consumed(
            tenant_id=TENANT,
            workspace_id=WORKSPACE,
            actor_id=ACTOR,
            provider_account_hash=ACCOUNT,
            provider_day_key="liepin:account-hash-a:2026-05-07",
        )
        == 0
    )


def test_failed_after_possible_consumption_consumes_budget_conservatively(tmp_path: Path) -> None:
    store = _store(tmp_path)
    attempt = _reserve(store, "candidate-after")
    store.transition_detail_attempt(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        attempt_id=attempt.attempt_id,
        state="started",
        consumption_state="not_consumed",
        worker_command_id="cmd-after",
    )

    failed = store.transition_detail_attempt(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        attempt_id=attempt.attempt_id,
        state="failed_after_possible_consumption",
        consumption_state="possibly_consumed",
        raw_evidence_ref="artifact:browser-crash-after-dispatch",
    )

    assert failed.consumption_state == "possibly_consumed"
    assert (
        store.count_detail_budget_consumed(
            tenant_id=TENANT,
            workspace_id=WORKSPACE,
            actor_id=ACTOR,
            provider_account_hash=ACCOUNT,
            provider_day_key="liepin:account-hash-a:2026-05-07",
        )
        == 1
    )


def test_invalid_transition_rejects_completed_directly_from_approved_not_started(tmp_path: Path) -> None:
    store = _store(tmp_path)
    attempt = _reserve(store, "candidate-invalid")

    with pytest.raises(ValueError, match="invalid Liepin detail attempt transition"):
        store.transition_detail_attempt(
            tenant_id=TENANT,
            workspace_id=WORKSPACE,
            actor_id=ACTOR,
            attempt_id=attempt.attempt_id,
            state="completed",
            consumption_state="consumed",
            raw_evidence_ref="artifact:detail",
        )


def _store(tmp_path: Path) -> LiepinStore:
    return LiepinStore(tmp_path / "liepin.sqlite3")


def _reserve(store: LiepinStore, candidate_provider_id: str):
    return store.reserve_detail_attempt(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        provider_account_hash=ACCOUNT,
        candidate_provider_id=candidate_provider_id,
        budget_date="2026-05-07",
        provider_day_key="liepin:account-hash-a:2026-05-07",
        timezone="Asia/Shanghai",
        idempotency_key=f"open:{candidate_provider_id}",
    )


def _complete(
    store: LiepinStore,
    candidate_provider_id: str,
    budget_date: str,
    provider_day_key: str,
    consumption_state: str,
) -> None:
    attempt = store.reserve_detail_attempt(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        provider_account_hash=ACCOUNT,
        candidate_provider_id=candidate_provider_id,
        budget_date=budget_date,
        provider_day_key=provider_day_key,
        timezone="Asia/Shanghai",
        idempotency_key=f"open:{candidate_provider_id}",
    )
    store.transition_detail_attempt(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        attempt_id=attempt.attempt_id,
        state="started",
        consumption_state="not_consumed",
        worker_command_id=f"cmd-{candidate_provider_id}",
    )
    if consumption_state == "consumed":
        state = "completed"
    elif consumption_state == "possibly_consumed":
        state = "failed_after_possible_consumption"
    else:
        state = "unknown"
    store.transition_detail_attempt(
        tenant_id=TENANT,
        workspace_id=WORKSPACE,
        actor_id=ACTOR,
        attempt_id=attempt.attempt_id,
        state=state,
        consumption_state=consumption_state,
        raw_evidence_ref=f"artifact:{candidate_provider_id}",
    )
