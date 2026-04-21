from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from pydantic_ai import Agent

from seektalent.config import AppSettings
from seektalent.llm import build_model, build_model_settings, build_output_spec
from seektalent.models import (
    ReflectionAdvice,
    ReflectionAdviceDraft,
    ReflectionContext,
    ReflectionFilterAdvice,
    ReflectionKeywordAdvice,
)
from seektalent.prompting import LoadedPrompt, json_block


def _join_terms(terms: Iterable[str]) -> str:
    return ", ".join(terms)


def _keyword_summary(keyword_advice: ReflectionKeywordAdvice) -> str:
    parts: list[str] = []
    if keyword_advice.suggested_activate_terms:
        parts.append(f"Activate {_join_terms(keyword_advice.suggested_activate_terms)} from the reserve term bank.")
    if keyword_advice.suggested_keep_terms:
        parts.append(f"Keep {_join_terms(keyword_advice.suggested_keep_terms)}.")
    if keyword_advice.suggested_deprioritize_terms:
        parts.append(f"De-prioritize {_join_terms(keyword_advice.suggested_deprioritize_terms)}.")
    if keyword_advice.suggested_drop_terms:
        parts.append(f"Drop {_join_terms(keyword_advice.suggested_drop_terms)}.")
    return " ".join(parts) if parts else "No keyword changes."


def _filter_summary(draft: ReflectionAdviceDraft) -> str:
    parts: list[str] = []
    if draft.filter_advice.suggested_keep_filter_fields:
        parts.append(f"keep filters {_join_terms(draft.filter_advice.suggested_keep_filter_fields)}")
    if draft.filter_advice.suggested_drop_filter_fields:
        parts.append(f"drop filters {_join_terms(draft.filter_advice.suggested_drop_filter_fields)}")
    if draft.filter_advice.suggested_add_filter_fields:
        parts.append(f"add filters {_join_terms(draft.filter_advice.suggested_add_filter_fields)}")
    return "; ".join(parts) if parts else "no filter changes"


def _term_key(term: str) -> str:
    return " ".join(term.strip().split()).casefold()


def _untried_admitted_terms(context: ReflectionContext) -> list[str]:
    term_index = {_term_key(item.term): item for item in context.requirement_sheet.initial_query_term_pool}
    tried_families = {
        candidate.family
        for record in context.sent_query_history
        for term in record.query_terms
        if (candidate := term_index.get(_term_key(term))) is not None
    }
    terms: list[str] = []
    seen_families: set[str] = set()
    for item in sorted(
        context.requirement_sheet.initial_query_term_pool,
        key=lambda item: (item.priority, item.first_added_round, item.family),
    ):
        if item.queryability != "admitted" or item.retrieval_role == "role_anchor":
            continue
        if item.family in tried_families or item.family in seen_families:
            continue
        terms.append(item.term)
        seen_families.add(item.family)
    return terms


def _top_pool_is_strong(context: ReflectionContext) -> bool:
    strong_fit_count = sum(
        1
        for item in context.top_candidates
        if item.fit_bucket == "fit"
        and item.overall_score >= 80
        and item.must_have_match_score >= 70
        and item.risk_score <= 30
    )
    return len(context.top_candidates) >= 10 and strong_fit_count >= 5


def _candidate_line(candidate, rank: int) -> str:  # noqa: ANN001
    return (
        f"- {rank}. {candidate.resume_id}: {candidate.fit_bucket}, score={candidate.overall_score}, "
        f"must={candidate.must_have_match_score}, risk={candidate.risk_score}; {candidate.reasoning_summary}"
    )


def render_reflection_prompt(context: ReflectionContext) -> str:
    plan = context.current_retrieval_plan
    observation = context.search_observation
    attempts = [
        f"- attempt {item.attempt_no}: raw={item.raw_candidate_count}, "
        f"new={item.batch_unique_new_count}, duplicates={item.batch_duplicate_count}, "
        f"exhausted={item.exhausted_reason or '(none)'}"
        for item in context.search_attempts[:8]
    ]
    top_candidates = [_candidate_line(candidate, index) for index, candidate in enumerate(context.top_candidates[:8], start=1)]
    dropped_candidates = [
        _candidate_line(candidate, index) for index, candidate in enumerate(context.dropped_candidates[:5], start=1)
    ]
    failures = [
        f"- {item.resume_id}: {item.error_message}"
        for item in context.scoring_failures[:5]
    ]
    sent_queries = [
        f"- round {record.round_no}: {', '.join(record.query_terms)}; {record.keyword_query}"
        for record in context.sent_query_history[-8:]
    ]
    exact_data = {
        "round_no": context.round_no,
        "current_query_terms": plan.query_terms,
        "projected_filter_fields": sorted(plan.projected_cts_filters),
        "top_candidate_ids": [item.resume_id for item in context.top_candidates[:8]],
        "dropped_candidate_ids": [item.resume_id for item in context.dropped_candidates[:5]],
        "stop_advice_fields": ["suggest_stop", "suggested_stop_reason"],
    }
    return "\n\n".join(
        [
            "TASK\nReview this retrieval round and return structured keyword/filter advice plus stop advice.",
            (
                "ROUND RESULT\n"
                f"- Round: {context.round_no}\n"
                f"- Requested: {observation.requested_count}\n"
                f"- Counts: raw={observation.raw_candidate_count}, new={observation.unique_new_count}, "
                f"shortage={observation.shortage_count}\n"
                f"- Fetch attempts: {observation.fetch_attempt_count}\n"
                f"- Exhausted reason: {observation.exhausted_reason or '(none)'}\n"
                f"- Adapter notes: {', '.join(observation.adapter_notes) or '(none)'}"
            ),
            (
                "CURRENT QUERY\n"
                f"- Terms: {', '.join(plan.query_terms) or '(none)'}\n"
                f"- Keyword query: {plan.keyword_query}\n"
                f"- Non-location filters: {plan.projected_cts_filters or {}}\n"
                f"- Rationale: {plan.rationale}"
            ),
            "SEARCH ATTEMPTS\n" + ("\n".join(attempts) if attempts else "- (none)"),
            "SENT QUERY HISTORY\n" + ("\n".join(sent_queries) if sent_queries else "- (none)"),
            "TOP CANDIDATES\n" + ("\n".join(top_candidates) if top_candidates else "- (empty)"),
            "DROPPED CANDIDATES\n" + ("\n".join(dropped_candidates) if dropped_candidates else "- (none)"),
            "SCORING FAILURES\n" + ("\n".join(failures) if failures else "- (none)"),
            "UNTRIED ADMITTED TERMS\n" + (_join_terms(_untried_admitted_terms(context)) or "(none)"),
            json_block("EXACT DATA", exact_data),
        ]
    )


def materialize_reflection_advice(*, context: ReflectionContext, draft: ReflectionAdviceDraft) -> ReflectionAdvice:
    keyword_advice = ReflectionKeywordAdvice(
        suggested_activate_terms=draft.keyword_advice.suggested_activate_terms,
        suggested_keep_terms=draft.keyword_advice.suggested_keep_terms,
        suggested_deprioritize_terms=draft.keyword_advice.suggested_deprioritize_terms,
        suggested_drop_terms=draft.keyword_advice.suggested_drop_terms,
    )
    keyword_summary = _keyword_summary(keyword_advice)
    untried_terms = _untried_admitted_terms(context)
    suppress_reflection_stop_advice = draft.suggest_stop and untried_terms and not _top_pool_is_strong(context)
    suggest_stop = draft.suggest_stop and not suppress_reflection_stop_advice
    suggested_stop_reason = draft.suggested_stop_reason if suggest_stop else None
    new_count = context.search_observation.unique_new_count
    noun = "candidate" if new_count == 1 else "candidates"
    summary_parts = [f"Round {context.round_no} yielded {new_count} new {noun}."]
    summary_parts.append(f"Keywords: {keyword_summary}")
    summary_parts.append(f"Filters: {_filter_summary(draft)}.")
    if suggest_stop and suggested_stop_reason:
        summary_parts.append(f"Stop: {suggested_stop_reason}.")
    elif suppress_reflection_stop_advice:
        summary_parts.append(f"Continue: untried admitted reserve terms remain: {_join_terms(untried_terms[:3])}.")
    else:
        summary_parts.append("Continue.")
    return ReflectionAdvice(
        keyword_advice=keyword_advice,
        filter_advice=ReflectionFilterAdvice(
            suggested_keep_filter_fields=draft.filter_advice.suggested_keep_filter_fields,
            suggested_drop_filter_fields=draft.filter_advice.suggested_drop_filter_fields,
            suggested_add_filter_fields=draft.filter_advice.suggested_add_filter_fields,
        ),
        suggest_stop=suggest_stop,
        suggested_stop_reason=suggested_stop_reason,
        reflection_summary=" ".join(summary_parts),
    )


class ReflectionCritic:
    def __init__(self, settings: AppSettings, prompt: LoadedPrompt) -> None:
        self.settings = settings
        self.prompt = prompt

    def _get_agent(self) -> Agent[None, ReflectionAdviceDraft]:
        model = build_model(self.settings.reflection_model)
        return cast(Agent[None, ReflectionAdviceDraft], Agent(
            model=model,
            output_type=build_output_spec(self.settings.reflection_model, model, ReflectionAdviceDraft),
            system_prompt=self.prompt.content,
            model_settings=build_model_settings(
                self.settings,
                self.settings.reflection_model,
                enable_thinking=self.settings.reflection_enable_thinking,
            ),
            retries=0,
            output_retries=2,
        ))

    async def reflect(self, *, context: ReflectionContext) -> ReflectionAdvice:
        result = await self._get_agent().run(render_reflection_prompt(context))
        return materialize_reflection_advice(context=context, draft=result.output)
