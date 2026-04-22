from __future__ import annotations

from seektalent.models import QueryTermCandidate, SentQueryRecord


def select_company_seed_terms(
    pool: list[QueryTermCandidate],
    sent_history: list[SentQueryRecord],
    forced_families: set[str],
    max_terms: int = 2,
) -> list[QueryTermCandidate]:
    if max_terms < 2:
        return []

    anchor = next((item for item in pool if _is_admitted_anchor(item)), None)
    if anchor is None:
        return []

    sent_families = _sent_families(pool, sent_history)
    blocked_families = sent_families | forced_families
    company = next(
        (
            item
            for item in pool
            if _is_admitted_company(item) and item.family not in blocked_families
        ),
        None,
    )
    if company is None:
        return []
    return [anchor, company]


def _is_admitted_anchor(item: QueryTermCandidate) -> bool:
    return item.queryability == "admitted" and item.active and item.retrieval_role == "role_anchor"


def _is_admitted_company(item: QueryTermCandidate) -> bool:
    return item.queryability == "admitted" and item.active and item.retrieval_role == "target_company"


def _sent_families(pool: list[QueryTermCandidate], sent_history: list[SentQueryRecord]) -> set[str]:
    term_index = {item.term.casefold(): item for item in pool}
    families: set[str] = set()
    for record in sent_history:
        for term in record.query_terms:
            candidate = term_index.get(term.casefold())
            if candidate is not None:
                families.add(candidate.family)
    return families
