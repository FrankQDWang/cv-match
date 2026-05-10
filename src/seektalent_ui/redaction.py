from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any


REDACTED = "[REDACTED]"

SENSITIVE_KEY_TOKENS = {
    "access_token",
    "accesstoken",
    "api_key",
    "apikey",
    "authorization",
    "authheader",
    "bearer",
    "browsercontext",
    "cdp",
    "cookie",
    "csrf",
    "localstorage",
    "password",
    "playwright",
    "provider_payload",
    "raw_profile",
    "raw_provider_payload",
    "raw_resume",
    "rawpayload",
    "refresh_token",
    "refreshtoken",
    "secret",
    "sessionstorage",
    "set-cookie",
    "session_token",
    "sessiontoken",
    "storagestate",
    "websocketdebuggerurl",
    "websocket_endpoint",
    "wsendpoint",
}
SENSITIVE_EXACT_KEYS = {"authorization", "cookie", "csrf", "password", "secret", "token"}
SENSITIVE_VALUE_MARKERS = {
    "authorization",
    "browsercontext",
    "cookie",
    "localstorage",
    "rawpayload",
    "sessionstorage",
    "set-cookie",
    "storagestate",
    "websocketdebuggerurl",
    "websocket_endpoint",
    "wsendpoint",
}
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"\bBasic\s+[A-Za-z0-9+/=-]+", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"\bcdp://\S+", re.IGNORECASE),
    re.compile(r"\bwss?://\S*(?:devtools|debugger|cdp|playwright|browser|websocketdebuggerurl|wsendpoint)\S*", re.IGNORECASE),
    re.compile(
        r"(?:^|[;\s])[-A-Za-z0-9_]*(?:"
        r"access[-_]?token|api[-_]?key|auth|cdp|cookie|csrf|password|refresh[-_]?token|secret|session|token"
        r")[-A-Za-z0-9_]*=[^;\s]+",
        re.IGNORECASE,
    ),
)


def redact_event_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        redacted_index = 0
        for key, item in value.items():
            key_text = str(key)
            if _contains_forbidden_key(key_text):
                redacted[f"redacted_{redacted_index}"] = REDACTED
                redacted_index += 1
                continue
            redacted[key_text] = redact_event_payload(item)
        return redacted
    if isinstance(value, list):
        return [redact_event_payload(item) for item in value]
    if isinstance(value, tuple):
        return [redact_event_payload(item) for item in value]
    if isinstance(value, str):
        if _contains_secret_value(value):
            return REDACTED
        return value
    if value is None or isinstance(value, bool | int | float):
        return value
    return str(value)


def redact_text(value: str | None) -> str | None:
    if value is None:
        return None
    if _contains_secret_value(value):
        return REDACTED
    return value


def _contains_forbidden_key(value: str) -> bool:
    compact = _compact_token(value)
    lowered = value.casefold()
    return compact in SENSITIVE_EXACT_KEYS or any(
        token in lowered or _compact_token(token) in compact for token in SENSITIVE_KEY_TOKENS
    )


def _contains_secret_value(value: str) -> bool:
    compact = _compact_token(value)
    return any(_compact_token(marker) in compact for marker in SENSITIVE_VALUE_MARKERS) or any(
        pattern.search(value) for pattern in SENSITIVE_VALUE_PATTERNS
    )


def _compact_token(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())
