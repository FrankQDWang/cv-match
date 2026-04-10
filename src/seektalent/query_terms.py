from __future__ import annotations

from collections.abc import Sequence


def normalized_query_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).strip()


def query_terms_hit(query_terms: Sequence[str], capability: str) -> int:
    normalized_capability = normalized_query_text(capability).casefold()
    if not normalized_capability:
        return 0
    for term in query_terms:
        normalized_term = normalized_query_text(term).casefold()
        if (
            normalized_term
            and (
                normalized_term in normalized_capability
                or normalized_capability in normalized_term
            )
        ):
            return 1
    return 0


__all__ = ["normalized_query_text", "query_terms_hit"]
