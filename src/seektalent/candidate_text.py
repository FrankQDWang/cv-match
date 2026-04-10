from __future__ import annotations

from typing import Sequence

from seektalent.models import stable_deduplicate


def build_candidate_search_text(
    *,
    role_title: str | None = None,
    industry: str | None = None,
    locations: Sequence[str | None] = (),
    projects: Sequence[str] = (),
    work_summaries: Sequence[str] = (),
    education_summaries: Sequence[str] = (),
    work_experience_summaries: Sequence[str] = (),
) -> str:
    sections = [
        _section("Target role", role_title),
        _section("Industry", industry),
        _section("Location", ", ".join(_clean_items(locations))),
        _section("Projects", ", ".join(_clean_items(projects))),
        _section("Work summary", ", ".join(_clean_items(work_summaries))),
        *[_section("Experience", item) for item in _clean_items(work_experience_summaries)],
        *[_section("Education", item) for item in _clean_items(education_summaries)],
    ]
    return " ".join(section for section in sections if section)


def _section(label: str, value: str | None) -> str:
    clean = _clean_text(value)
    if not clean:
        return ""
    if clean.endswith((".", "!", "?", "。", "！", "？")):
        return f"{label}: {clean}"
    return f"{label}: {clean}."


def _clean_items(values: Sequence[str | None]) -> list[str]:
    return stable_deduplicate([_clean_text(value) for value in values])


def _clean_text(value: str | None) -> str:
    return " ".join((value or "").split()).strip()
