from __future__ import annotations

from collections.abc import Callable
import asyncio
from dataclasses import dataclass
import inspect
from typing import Any

from seektalent.config import AppSettings
from seektalent.core.retrieval.provider_contract import SearchRequest
from seektalent.progress import ProgressCallback
from seektalent.providers.liepin.client import LiepinWorkerClient, build_liepin_worker_client
from seektalent.providers.liepin.worker_contracts import LiepinWorkerModeError
from seektalent_ui.workbench_store import WorkbenchSourceRunJobContext, WorkbenchStore


RuntimeFactory = Callable[[AppSettings], object]


@dataclass(frozen=True)
class ExtractedRequirementTriage:
    must_haves: list[str]
    nice_to_haves: list[str]
    synonyms: list[str]
    seniority_filters: list[str]
    exclusions: list[str]
    generated_query_hints: list[str]


def extract_requirement_triage(
    *,
    session,
    settings: AppSettings,
    runtime_factory: RuntimeFactory,
    progress_callback: ProgressCallback | None = None,
) -> ExtractedRequirementTriage:
    runtime = runtime_factory(settings)
    extractor = getattr(runtime, "extract_requirements", None)
    if extractor is None:
        raise RuntimeError("Runtime does not support requirement extraction.")
    requirement_sheet = extractor(
        job_title=session.job_title,
        jd=session.jd_text,
        notes=session.notes,
        progress_callback=progress_callback,
    )
    return _triage_from_requirement_sheet(requirement_sheet)


def run_cts_source_run(
    *,
    context: WorkbenchSourceRunJobContext,
    store: WorkbenchStore,
    settings: AppSettings,
    runtime_factory: RuntimeFactory,
    progress_callback: ProgressCallback | None = None,
) -> None:
    runtime = runtime_factory(settings)
    run_kwargs: dict[str, object] = {
        "job_title": context.session.job_title,
        "jd": context.session.jd_text,
        "notes": _notes_with_triage(context),
        "progress_callback": progress_callback,
    }
    if _runtime_run_accepts_start_callback(runtime):
        run_kwargs["runtime_start_callback"] = lambda run_id: store.attach_source_run_runtime_run_id(
            context=context,
            runtime_run_id=run_id,
        )
    artifacts = runtime.run(**run_kwargs)
    store.complete_cts_source_run_with_candidate_results(context=context, artifacts=artifacts)


def run_liepin_card_source_run(
    *,
    context: WorkbenchSourceRunJobContext,
    store: WorkbenchStore,
    settings: AppSettings,
    worker_client: LiepinWorkerClient | None = None,
) -> None:
    connection = store.get_liepin_source_connection_for_job_context(context=context)
    if connection is None or connection.status != "connected" or connection.provider_account_hash is None:
        raise LiepinWorkerModeError("Liepin source run requires a connected source account.")
    client = worker_client or build_liepin_worker_client(settings)
    result = asyncio.run(
        client.search(
            _liepin_card_search_request(context=context, connection_id=connection.connection_id),
            round_no=1,
            trace_id=context.job.job_id,
            provider_account_hash=connection.provider_account_hash,
        )
    )
    store.complete_liepin_card_source_run_with_search_result(context=context, result=result)


def _notes_with_triage(context: WorkbenchSourceRunJobContext) -> str:
    triage = context.triage
    sections = [
        context.session.notes.strip(),
        "Approved requirement triage:",
        f"must_haves: {_bounded_join(triage.must_haves)}",
        f"nice_to_haves: {_bounded_join(triage.nice_to_haves)}",
        f"synonyms: {_bounded_join(triage.synonyms)}",
        f"seniority_filters: {_bounded_join(triage.seniority_filters)}",
        f"exclusions: {_bounded_join(triage.exclusions)}",
        f"generated_query_hints: {_bounded_join(triage.generated_query_hints)}",
    ]
    return "\n".join(section for section in sections if section)


def _liepin_card_search_request(*, context: WorkbenchSourceRunJobContext, connection_id: str) -> SearchRequest:
    terms = _query_terms(context)
    return SearchRequest(
        query_terms=terms,
        query_role="primary",
        keyword_query=" ".join(terms),
        adapter_notes=[context.session.notes],
        runtime_constraints=[],
        fetch_mode="summary",
        page_size=30,
        provider_context={
            "liepin_tenant_id": "local",
            "liepin_workspace_id": context.session.workspace_id,
            "liepin_actor_id": context.session.owner_user_id,
            "liepin_connection_id": connection_id,
            "query_instance_id": context.job.job_id,
            "query_fingerprint": context.job.job_id,
        },
    )


def _query_terms(context: WorkbenchSourceRunJobContext) -> list[str]:
    source_terms = [
        *context.triage.generated_query_hints,
        *context.triage.must_haves,
        *context.triage.synonyms,
        context.session.job_title,
    ]
    terms: list[str] = []
    seen: set[str] = set()
    for value in source_terms:
        text = value.strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        terms.append(text)
        if len(terms) >= 8:
            break
    return terms or [context.session.job_title]


def _runtime_run_accepts_start_callback(runtime: object) -> bool:
    try:
        signature = inspect.signature(runtime.run)
    except (AttributeError, TypeError, ValueError):
        return False
    parameters = signature.parameters
    if "runtime_start_callback" in parameters:
        return True
    return any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values())


def _triage_from_requirement_sheet(requirement_sheet: object) -> ExtractedRequirementTriage:
    return ExtractedRequirementTriage(
        must_haves=_unique_bounded_strings(_object_list(requirement_sheet, "must_have_capabilities")),
        nice_to_haves=_unique_bounded_strings(_object_list(requirement_sheet, "preferred_capabilities")),
        synonyms=[],
        seniority_filters=[],
        exclusions=_unique_bounded_strings(_object_list(requirement_sheet, "exclusion_signals")),
        generated_query_hints=_query_hints_from_requirement_sheet(requirement_sheet),
    )


def _query_hints_from_requirement_sheet(requirement_sheet: object) -> list[str]:
    terms: list[object] = [
        *_object_list(requirement_sheet, "initial_query_term_pool"),
        *_object_list(requirement_sheet, "title_anchor_terms"),
    ]
    values: list[str] = []
    for term in terms:
        if isinstance(term, str):
            values.append(term)
            continue
        term_value = _object_attr(term, "term")
        if isinstance(term_value, str):
            values.append(term_value)
    return _unique_bounded_strings(values, max_items=12)


def _object_list(value: object, attr: str) -> list[object]:
    item = _object_attr(value, attr)
    if item is None:
        return []
    if isinstance(item, list):
        return item
    if isinstance(item, tuple):
        return list(item)
    return []


def _object_attr(value: object, attr: str) -> Any:
    if isinstance(value, dict):
        return value.get(attr)
    return getattr(value, attr, None)


def _unique_bounded_strings(values: list[object], *, max_items: int = 20, max_chars: int = 180) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        if len(text) > max_chars:
            text = text[:max_chars].rstrip()
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        results.append(text)
        if len(results) >= max_items:
            break
    return results


def _bounded_join(values: list[str], *, max_items: int = 12, max_chars: int = 800) -> str:
    text = "; ".join(values[:max_items])
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."
