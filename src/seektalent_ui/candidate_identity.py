from __future__ import annotations

import hashlib
import re


_DATE_PATTERN = re.compile(r"(?P<year>19\d{2}|20\d{2})(?:[.\-/年](?P<month>0?[1-9]|1[0-2]))?")
_CURRENT_MARKERS = ("至今", "现在", "目前", "present", "current", "now")
_MASKED_NAME_EXACT = {"", "-", "--", "匿名", "候选人", "未知", "保密"}


def workbench_candidate_field_identity_keys(
    *,
    display_name: str,
    title: str,
    company: str,
    location: str,
    summary: str,
) -> tuple[str, ...]:
    del summary
    name = _normalize_identity_text(display_name)
    if not name or _is_masked_name(display_name):
        return ()

    title_norm = _normalize_identity_text(title)
    company_norm = _normalize_identity_text(company)
    location_norm = _normalize_identity_text(location)
    if not (title_norm and company_norm and location_norm):
        return ()
    return (f"field:name-company-title-location:{name}:{company_norm}:{title_norm}:{location_norm}",)


def workbench_resume_freshness_key(*texts: str) -> tuple[int, int, int]:
    text = " ".join(value for value in texts if value)
    lowered = text.casefold()
    has_current_marker = any(marker in lowered for marker in _CURRENT_MARKERS)
    latest_year = 0
    latest_month = 0
    for match in _DATE_PATTERN.finditer(text):
        year = int(match.group("year"))
        month = int(match.group("month") or "12")
        if (year, month) > (latest_year, latest_month):
            latest_year = year
            latest_month = month
    return (1 if has_current_marker else 0, latest_year, latest_month)


def public_identity_id(identity_key: str) -> str:
    if identity_key.startswith("identity:"):
        return identity_key.removeprefix("identity:")
    if identity_key.startswith("field:"):
        return _digest_identity_key(identity_key)
    return identity_key.removeprefix("provider:").removeprefix("review:")


def _digest_identity_key(key: str) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return f"identity_{digest}"


def _normalize_identity_text(value: str) -> str:
    return "".join(char.casefold() for char in value.strip() if char.isalnum())


def _is_masked_name(value: str) -> bool:
    text = value.strip()
    normalized = _normalize_identity_text(text)
    if normalized in _MASKED_NAME_EXACT:
        return True
    if "*" in text:
        return True
    if "某" in text:
        return True
    if text.endswith(("先生", "女士", "小姐")):
        return True
    if re.fullmatch(r"[A-Za-z]+\*+", text):
        return True
    if re.fullmatch(r"候选人\d+", text):
        return True
    return False
