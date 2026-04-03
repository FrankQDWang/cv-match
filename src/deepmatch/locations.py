from __future__ import annotations

from deepmatch.models import unique_strings


def normalize_location(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).strip()


def normalize_locations(values: list[str | None]) -> list[str]:
    cleaned = [normalize_location(value) for value in values]
    return unique_strings([value for value in cleaned if value])


__all__ = ["normalize_location", "normalize_locations"]
