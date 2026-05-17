from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, Literal, Protocol, cast

from seektalent.providers.liepin.dokobot_actions import DokoBotActionReadiness
from seektalent.providers.liepin.worker_contracts import (
    LiepinCardSearchResponse,
    LiepinSafeCardSummary,
    LiepinWorkerCandidateCard,
    LoginHandoff,
    LoginRelayCompleteResult,
    SessionStatus,
)
from seektalent.providers.pi_agent.capabilities import DokoBotCapabilities
from seektalent.providers.pi_agent.contracts import (
    PiAgentActionTraceEntry,
    PiAgentActionType,
    PiAgentFailureCode,
    PiAgentResult,
    PiAgentResultStatus,
    PiArtifactRef,
    PiBackendMode,
    ProtectedArtifactClass,
)


ArtifactWriter = Callable[[bytes, ProtectedArtifactClass, str], PiArtifactRef]
ProviderState = Literal[
    "ready",
    "login_required",
    "verification_required",
    "risk_control",
    "unsupported_route",
    "timeout",
    "capability_unavailable",
]

TRACE_REDACTION_POLICY_ID = "liepin-trace-redaction-v1"
SAFE_CARD_TEXT_REDACTION_POLICY_ID = "liepin-card-summary-redaction-v1"
ACTION_TRACE_PROVIDER_SKILL_ID = "liepin.search_cards.v1"
UNSAFE_TEXT_PATTERN = re.compile(
    r"(@|bearer\s+|cookie|storage|session=|secret|<[^>]+>|(?:\+?86[-\s]?)?1[3-9]\d{9})",
    re.IGNORECASE,
)


class DokoBotActionSurface(Protocol):
    def submit_keyword_search(self, *, keyword_query: str, source_run_id: str) -> None: ...

    def read_card_page(self, *, page_index: int, page_size: int, remaining_cards: int) -> dict[str, Any]: ...

    def turn_page(self, *, page_index: int) -> None: ...

    def detect_provider_state(self) -> str | dict[str, Any]: ...

    def provider_account_hash(self) -> str | None: ...


class DokoBotActionTransportUnavailable(RuntimeError):
    pass


class DokoBotActionTransportSession:
    def __init__(
        self,
        *,
        capabilities: DokoBotCapabilities,
        action_surface: DokoBotActionSurface | None,
        artifact_writer: ArtifactWriter,
        connection_id: str = "liepin-dokobot-action",
    ) -> None:
        self._capabilities = capabilities
        self._action_surface = action_surface
        self._artifact_writer = artifact_writer
        self._connection_id = connection_id

    def detect_provider_state(self) -> DokoBotActionReadiness:
        if not self._capabilities.can_execute_liepin_actions or self._action_surface is None:
            return DokoBotActionReadiness(
                state="capability_unavailable",
                failure_code=PiAgentFailureCode.DOKOBOT_ACTION_CAPABILITY_UNAVAILABLE,
            )
        try:
            return DokoBotActionReadiness(state=_provider_state_from_surface(self._action_surface.detect_provider_state()))
        except DokoBotActionTransportUnavailable:
            return DokoBotActionReadiness(
                state="capability_unavailable",
                failure_code=PiAgentFailureCode.DOKOBOT_ACTION_CAPABILITY_UNAVAILABLE,
            )

    def submit_keyword_search(self, *, keyword_query: str, source_run_id: str) -> None:
        self._surface().submit_keyword_search(keyword_query=keyword_query, source_run_id=source_run_id)

    def read_card_page(self, *, page_index: int, page_size: int, remaining_cards: int) -> LiepinCardSearchResponse:
        payload = self._surface().read_card_page(
            page_index=page_index,
            page_size=page_size,
            remaining_cards=remaining_cards,
        )
        return liepin_card_search_response_from_action_payload(payload, max_cards=remaining_cards)

    def turn_page(self, *, page_index: int) -> None:
        self._surface().turn_page(page_index=page_index)

    def write_action_trace(
        self,
        *,
        source_run_id: str,
        result_code: str,
        failure_code: PiAgentFailureCode | None,
    ) -> PiAgentResult:
        status = _status_from_result_code(result_code)
        trace = PiAgentActionTraceEntry(
            schema_version="pi-agent-action-trace-v1",
            timestamp=datetime.now(UTC),
            provider_skill_id=ACTION_TRACE_PROVIDER_SKILL_ID,
            interaction_id=f"{source_run_id}:dokobot_action:1",
            source_run_id=source_run_id,
            connection_id=self._connection_id,
            action_sequence=1,
            action_type=PiAgentActionType.LIEPIN_SUBMIT_KEYWORD_SEARCH,
            backend_mode=PiBackendMode.DOKOBOT_ACTION,
            capability_version=_capability_version(self._capabilities),
            safe_target_descriptor="liepin keyword search",
            result_code=cast(Literal["ok", "blocked", "failed", "partial"], result_code),
            duration_ms=0,
            retry_count=0,
            redaction_policy_id=TRACE_REDACTION_POLICY_ID,
            failure_code=failure_code,
        )
        trace_ref = self._artifact_writer(
            json.dumps(trace.model_dump(mode="json"), sort_keys=True).encode("utf-8"),
            ProtectedArtifactClass.REDACTED_EVIDENCE,
            TRACE_REDACTION_POLICY_ID,
        )
        return PiAgentResult(
            schema_version="pi-agent-result-v1",
            status=status,
            stop_reason=failure_code,
            action_trace_ref=trace_ref,
        )

    def session_status(
        self,
        *,
        connection_id: str,
        tenant: str | None = None,
        workspace: str | None = None,
        provider_account_hash: str | None = None,
    ) -> SessionStatus:
        del tenant, workspace
        readiness = self.detect_provider_state()
        if not readiness.is_ready:
            return SessionStatus(connectionId=connection_id, status="login_required", providerAccountHash=None)
        account_hash = self._surface().provider_account_hash()
        if not account_hash or (provider_account_hash is not None and account_hash != provider_account_hash):
            return SessionStatus(connectionId=connection_id, status="login_required", providerAccountHash=None)
        return SessionStatus(connectionId=connection_id, status="ready", providerAccountHash=account_hash)

    def complete_login_relay(self, *, connection_id: str) -> LoginRelayCompleteResult:
        status = self.session_status(connection_id=connection_id)
        if status.status != "ready":
            raise DokoBotActionTransportUnavailable("dokobot_action_login_not_verified")
        return LoginRelayCompleteResult(
            connectionId=connection_id,
            status="ready",
            providerAccountHash=status.provider_account_hash,
            fixtureOnly=False,
        )

    def login_handoff(
        self,
        *,
        connection_id: str,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
        provider_account_hash: str | None = None,
    ) -> LoginHandoff:
        del tenant_id, workspace_id, provider_account_hash
        if self.detect_provider_state().state == "capability_unavailable":
            raise DokoBotActionTransportUnavailable("dokobot_action_capability_unavailable")
        return LoginHandoff(
            connectionId=connection_id,
            handoffToken=f"dokobot-action:{sha256(connection_id.encode()).hexdigest()[:16]}",
            loginUrl="https://www.liepin.com/",
            expiresAt=(datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
        )

    def _surface(self) -> DokoBotActionSurface:
        if self._action_surface is None:
            raise DokoBotActionTransportUnavailable("dokobot_action_surface_unavailable")
        return self._action_surface


def liepin_card_search_response_from_action_payload(
    payload: dict[str, Any],
    *,
    max_cards: int,
) -> LiepinCardSearchResponse:
    raw_cards = payload.get("cards")
    cards_payload = raw_cards if isinstance(raw_cards, list) else []
    cards = [
        _card_from_action_payload(card_payload, provider_rank=index)
        for index, card_payload in enumerate(cards_payload[:max_cards], start=1)
        if isinstance(card_payload, dict)
    ]
    return LiepinCardSearchResponse(
        cards=cards,
        diagnostics=_string_list(payload.get("diagnostics")),
        exhausted=bool(payload.get("exhausted", False)),
        nextCursor=payload.get("nextCursor") if isinstance(payload.get("nextCursor"), str) else None,
        requestPayload=_safe_request_payload(payload.get("requestPayload")),
        rawCandidateCount=_raw_candidate_count(payload.get("rawCandidateCount"), len(cards)),
    )


def _card_from_action_payload(payload: dict[str, Any], *, provider_rank: int) -> LiepinWorkerCandidateCard:
    provider_subject_id = _string_value(payload, "providerSubjectId") or _string_value(payload, "provider_subject_id")
    provider_listing_id = _string_value(payload, "providerListingId") or _string_value(payload, "provider_listing_id")
    normalized_text = _safe_text_value(payload, "normalizedText") or _safe_text_value(payload, "normalized_text")
    summary_payload = _safe_card_summary_payload(payload.get("safeCardSummary") or payload.get("safe_card_summary"))
    safe_summary = LiepinSafeCardSummary.model_validate(summary_payload)
    if normalized_text is None:
        normalized_text = _summary_text(safe_summary)
    fingerprint = _string_value(payload, "syntheticCandidateFingerprint") or _synthetic_fingerprint(
        provider_subject_id=provider_subject_id,
        provider_listing_id=provider_listing_id,
        normalized_text=normalized_text,
        provider_rank=provider_rank,
    )
    return LiepinWorkerCandidateCard(
        payload=_safe_card_payload(
            payload,
            provider_rank=provider_rank,
            provider_subject_id=provider_subject_id,
            provider_listing_id=provider_listing_id,
        ),
        normalized_text=normalized_text,
        provider_subject_id=provider_subject_id,
        provider_listing_id=provider_listing_id,
        synthetic_candidate_fingerprint=fingerprint,
        identity_confidence="provider_subject_id" if provider_subject_id else "synthetic_fingerprint",
        extraction_source="dom_fallback",
        extractor_version="dokobot-action-v1",
        pii_classification="no_direct_contact",
        retention_policy="provider_snapshot_7d",
        access_scope="local_run_only",
        redaction_state="redacted",
        safeCardSummary=safe_summary,
    )


def _safe_card_summary_payload(value: object) -> dict[str, object]:
    source = value if isinstance(value, dict) else {}
    mapping = {
        "displayTitle": "display_title",
        "currentOrRecentCompany": "current_or_recent_company",
        "currentOrRecentTitle": "current_or_recent_title",
        "workYears": "work_years",
        "expectedCity": "expected_city",
        "educationLevel": "education_level",
        "schoolNames": "school_names",
        "majorNames": "major_names",
        "skillTags": "skill_tags",
        "jobIntention": "job_intention",
        "recentExperienceText": "recent_experience_text",
        "maskedName": "masked_name",
    }
    normalized: dict[str, object] = {}
    for raw_key, raw_value in source.items():
        key = mapping.get(raw_key, raw_key)
        if key in {"work_years", "age"}:
            if isinstance(raw_value, int) and raw_value >= 0:
                normalized[key] = raw_value
        elif key == "masked_name":
            normalized[key] = bool(raw_value)
        elif key in {"school_names", "major_names", "skill_tags"}:
            normalized[key] = tuple(item for item in _string_list(raw_value) if _clean_safe_text(item))
        elif isinstance(raw_value, str):
            safe = _clean_safe_text(raw_value)
            if safe is not None:
                normalized[key] = safe
    return normalized


def _safe_card_payload(
    payload: dict[str, Any],
    *,
    provider_rank: int,
    provider_subject_id: str | None,
    provider_listing_id: str | None,
) -> dict[str, object]:
    safe: dict[str, object] = {"providerRank": provider_rank}
    if provider_subject_id is not None:
        safe["providerSubjectId"] = provider_subject_id
    if provider_listing_id is not None:
        safe["providerListingId"] = provider_listing_id
    safe_summary_ref = _string_value(payload, "safeSummaryRef") or _string_value(payload, "safe_summary_ref")
    if safe_summary_ref is not None:
        safe["safeSummaryRef"] = safe_summary_ref
    return safe


def _status_from_result_code(result_code: str) -> PiAgentResultStatus:
    if result_code == "ok":
        return PiAgentResultStatus.SUCCEEDED
    if result_code == "blocked":
        return PiAgentResultStatus.BLOCKED
    if result_code == "partial":
        return PiAgentResultStatus.PARTIAL
    if result_code == "failed":
        return PiAgentResultStatus.FAILED
    raise ValueError(f"unsupported DokoBot action trace result_code: {result_code}")


def _provider_state_from_surface(value: str | dict[str, Any]) -> ProviderState:
    raw_state = value.get("state") if isinstance(value, dict) else value
    if raw_state in {
        "ready",
        "login_required",
        "verification_required",
        "risk_control",
        "unsupported_route",
        "timeout",
        "capability_unavailable",
    }:
        return cast(ProviderState, raw_state)
    return "unsupported_route"


def _capability_version(capabilities: DokoBotCapabilities) -> str:
    if capabilities.action_manifest_id and capabilities.action_manifest_version:
        return f"{capabilities.action_manifest_id}@{capabilities.action_manifest_version}"
    return capabilities.cli_version or "unknown"


def _raw_candidate_count(value: object, fallback: int) -> int:
    return value if isinstance(value, int) and value >= 0 else fallback


def _safe_request_payload(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    safe_keys = {"keyword", "pageSize", "pageIndex", "traceId"}
    return {key: item for key, item in value.items() if key in safe_keys and isinstance(item, str | int)}


def _string_value(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str):
        return None
    return _clean_safe_text(value)


def _safe_text_value(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return _clean_safe_text(value) if isinstance(value, str) else None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [item for item in value if isinstance(item, str)]


def _clean_safe_text(value: str) -> str | None:
    stripped = value.strip()
    if not stripped or UNSAFE_TEXT_PATTERN.search(stripped):
        return None
    return stripped


def _summary_text(summary: LiepinSafeCardSummary) -> str:
    parts = [
        summary.current_or_recent_title,
        summary.current_or_recent_company,
        " ".join(summary.skill_tags),
        summary.recent_experience_text,
    ]
    text = " ".join(part for part in parts if part)
    return text or "Liepin candidate card"


def _synthetic_fingerprint(
    *,
    provider_subject_id: str | None,
    provider_listing_id: str | None,
    normalized_text: str,
    provider_rank: int,
) -> str:
    content = json.dumps(
        {
            "provider_subject_id": provider_subject_id,
            "provider_listing_id": provider_listing_id,
            "normalized_text": normalized_text,
            "provider_rank": provider_rank,
        },
        sort_keys=True,
    ).encode("utf-8")
    return f"liepin:dokobot:{sha256(content).hexdigest()[:16]}"
