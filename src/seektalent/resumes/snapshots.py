from __future__ import annotations

from hashlib import sha256
from typing import Any

from seektalent.flywheel.store import canonical_json


def canonical_resume_snapshot_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    return raw_payload


def snapshot_sha256(raw_payload: dict[str, Any]) -> str:
    payload = canonical_resume_snapshot_payload(raw_payload)
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()
