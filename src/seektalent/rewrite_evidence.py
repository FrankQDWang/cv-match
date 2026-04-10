from __future__ import annotations

import re

from seektalent.models import (
    RequirementSheet,
    RetrievedCandidate_t,
    RewriteTermCandidate,
    RewriteTermPool,
    RewriteTermRejected,
    SearchExecutionPlan_t,
    SearchExecutionResult_t,
    SearchScoringResult_t,
    stable_deduplicate,
)
from seektalent.query_terms import normalized_query_text, query_terms_hit


TOP_EVIDENCE_CANDIDATES = 5
MAX_ACCEPTED_REWRITE_TERMS = 6
TECH_TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9+.#/-]{1,}")
SPLIT_PATTERN = re.compile(r"[,|/;；、]+")
GENERIC_JUNK_TERMS = {
    "work",
    "summary",
    "experience",
    "education",
    "industry",
    "location",
    "target",
    "role",
    "projects",
    "负责",
    "推进",
    "优化",
    "沟通",
    "协作",
    "落地",
    "团队",
}
PACK_TOKEN_STOPWORDS = {"ai", "engineering", "agent"}


def build_rewrite_term_pool(
    requirement_sheet: RequirementSheet,
    plan: SearchExecutionPlan_t,
    execution_result: SearchExecutionResult_t,
    scoring_result: SearchScoringResult_t,
) -> RewriteTermPool:
    candidate_lookup = {
        candidate.candidate_id: candidate
        for candidate in execution_result.deduplicated_candidates
    }
    top_candidates = [
        candidate_lookup[row.candidate_id]
        for row in scoring_result.scored_candidates
        if row.fit == 1 and row.candidate_id in candidate_lookup
    ][:TOP_EVIDENCE_CANDIDATES]
    if not top_candidates:
        return RewriteTermPool()

    current_query_terms = stable_deduplicate(plan.query_terms)
    unmet_must_haves = [
        capability
        for capability in requirement_sheet.must_have_capabilities
        if query_terms_hit(current_query_terms, capability) == 0
    ]
    pack_terms = _pack_terms(plan.knowledge_pack_ids)
    aggregated: dict[str, dict[str, set[str]]] = {}
    rejected: list[RewriteTermRejected] = []

    for candidate in top_candidates:
        for field_name, field_values in _candidate_field_values(candidate).items():
            for term in _field_terms(field_name, field_values):
                normalized_term = normalized_query_text(term)
                if not normalized_term:
                    continue
                if query_terms_hit(current_query_terms, normalized_term) == 1:
                    rejected.append(
                        RewriteTermRejected(
                            term=normalized_term,
                            source_candidate_ids=[candidate.candidate_id],
                            source_fields=[field_name],
                            reason="already_in_query",
                        )
                    )
                    continue
                bucket = aggregated.setdefault(
                    normalized_term.casefold(),
                    {"term": {normalized_term}, "candidate_ids": set(), "fields": set()},
                )
                bucket["term"] = {normalized_term}
                bucket["candidate_ids"].add(candidate.candidate_id)
                bucket["fields"].add(field_name)

    accepted: list[RewriteTermCandidate] = []
    for bucket in aggregated.values():
        term = next(iter(bucket["term"]))
        source_candidate_ids = sorted(bucket["candidate_ids"])
        source_fields = sorted(bucket["fields"])
        if _is_generic_junk(term):
            rejected.append(
                RewriteTermRejected(
                    term=term,
                    source_candidate_ids=source_candidate_ids,
                    source_fields=source_fields,
                    reason="generic_junk",
                )
            )
            continue
        if not _passes_topic_drift_gate(
            term,
            current_query_terms=current_query_terms,
            unmet_must_haves=unmet_must_haves,
            pack_terms=pack_terms,
        ):
            rejected.append(
                RewriteTermRejected(
                    term=term,
                    source_candidate_ids=source_candidate_ids,
                    source_fields=source_fields,
                    reason="topic_drift",
                )
            )
            continue
        if len(source_candidate_ids) < 2 and not any(
            query_terms_hit([term], capability) == 1 for capability in unmet_must_haves
        ):
            rejected.append(
                RewriteTermRejected(
                    term=term,
                    source_candidate_ids=source_candidate_ids,
                    source_fields=source_fields,
                    reason="low_support",
                )
            )
            continue
        accepted.append(
            RewriteTermCandidate(
                term=term,
                source_candidate_ids=source_candidate_ids,
                source_fields=source_fields,
            )
        )

    accepted.sort(
        key=lambda item: (
            -_accepted_term_score(
                item,
                current_query_terms=current_query_terms,
                unmet_must_haves=unmet_must_haves,
                pack_terms=pack_terms,
            ),
            item.term.casefold(),
        )
    )
    return RewriteTermPool(
        accepted=accepted[:MAX_ACCEPTED_REWRITE_TERMS],
        rejected=sorted(
            rejected,
            key=lambda item: (item.reason, item.term.casefold()),
        ),
    )


def _candidate_field_values(candidate: RetrievedCandidate_t) -> dict[str, list[str]]:
    title = _first_text(
        candidate.raw_payload.get("expectedJobCategory"),
        candidate.raw_payload.get("title"),
    )
    values = {
        "title": [title] if title else [],
        "project_names": list(candidate.project_names),
        "work_summaries": list(candidate.work_summaries),
        "work_experience_summaries": list(candidate.work_experience_summaries),
        "search_text": [candidate.search_text],
    }
    return values


def _field_terms(field_name: str, values: list[str]) -> list[str]:
    terms: list[str] = []
    for value in values:
        clean = normalized_query_text(value)
        if not clean:
            continue
        if field_name != "search_text":
            pieces = [clean, *SPLIT_PATTERN.split(clean)]
            for piece in pieces:
                normalized_piece = normalized_query_text(piece)
                if _valid_phrase(normalized_piece):
                    terms.append(normalized_piece)
        terms.extend(TECH_TOKEN_PATTERN.findall(clean))
    return stable_deduplicate(terms)


def _valid_phrase(value: str) -> bool:
    if not value or len(value) < 2 or len(value) > 40:
        return False
    if value.isdigit():
        return False
    word_count = len(value.split())
    if word_count > 4:
        return False
    return True


def _passes_topic_drift_gate(
    term: str,
    *,
    current_query_terms: list[str],
    unmet_must_haves: list[str],
    pack_terms: list[str],
) -> bool:
    references = stable_deduplicate(
        current_query_terms + unmet_must_haves + pack_terms
    )
    return any(query_terms_hit([term], reference) == 1 for reference in references)


def _pack_terms(knowledge_pack_ids: list[str]) -> list[str]:
    return [
        token
        for token in stable_deduplicate(
            [
                normalized_query_text(token)
                for pack_id in knowledge_pack_ids
                for token in str(pack_id).split("_")
            ]
        )
        if token and token not in PACK_TOKEN_STOPWORDS
    ]


def _is_generic_junk(term: str) -> bool:
    normalized = normalized_query_text(term).casefold()
    if not normalized:
        return True
    if normalized in GENERIC_JUNK_TERMS:
        return True
    if not TECH_TOKEN_PATTERN.search(normalized) and any(
        marker in normalized for marker in GENERIC_JUNK_TERMS if len(marker) > 1
    ):
        return True
    return all(
        fragment in GENERIC_JUNK_TERMS
        for fragment in re.findall(r"[A-Za-z]+|[\u4e00-\u9fff]+", normalized)
        if fragment
    )


def _accepted_term_score(
    item: RewriteTermCandidate,
    *,
    current_query_terms: list[str],
    unmet_must_haves: list[str],
    pack_terms: list[str],
) -> float:
    score = float(len(item.source_candidate_ids))
    if any(query_terms_hit([item.term], capability) == 1 for capability in unmet_must_haves):
        score += 2.0
    if any(query_terms_hit([item.term], term) == 1 for term in current_query_terms):
        score += 1.0
    if any(query_terms_hit([item.term], term) == 1 for term in pack_terms):
        score += 0.5
    score += max((_field_weight(field) for field in item.source_fields), default=0.0)
    return score


def _field_weight(field_name: str) -> float:
    return {
        "project_names": 1.0,
        "work_summaries": 0.9,
        "work_experience_summaries": 0.8,
        "title": 0.7,
        "search_text": 0.5,
    }.get(field_name, 0.0)


def _first_text(*values: object) -> str:
    for value in values:
        clean = normalized_query_text(value)
        if clean:
            return clean
    return ""


__all__ = ["build_rewrite_term_pool"]
