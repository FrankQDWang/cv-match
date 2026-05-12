from __future__ import annotations

import json

from seektalent.config import AppSettings
from seektalent.corpus.store import CorpusStore
from seektalent_ui.models import (
    WorkbenchGraphCandidateResumeSnapshotResponse,
    WorkbenchResumeSnapshotEducationResponse,
    WorkbenchResumeSnapshotProfileResponse,
    WorkbenchResumeSnapshotProjectResponse,
    WorkbenchResumeSnapshotSourceEvidenceResponse,
    WorkbenchResumeSnapshotWorkExperienceResponse,
)
from seektalent_ui.models import WorkbenchGraphCandidateSummaryResponse
from seektalent_ui.workbench_candidate_graph import resolve_graph_candidate
from seektalent_ui.workbench_store import DEFAULT_TENANT_ID, WorkbenchStore, WorkbenchUser


def build_resume_snapshot_response(
    *,
    settings: AppSettings,
    graph_secret: str,
    store: WorkbenchStore,
    user: WorkbenchUser,
    session_id: str,
    graph_candidate_id: str,
) -> WorkbenchGraphCandidateResumeSnapshotResponse | None:
    candidate = resolve_graph_candidate(
        settings=settings,
        graph_secret=graph_secret,
        store=store,
        user=user,
        session_id=session_id,
        graph_candidate_id=graph_candidate_id,
    )
    if candidate is None:
        return None
    if not candidate.snapshot_sha256:
        return WorkbenchGraphCandidateResumeSnapshotResponse(
            graphCandidateId=graph_candidate_id,
            status="snapshot_not_found",
            reason="snapshot_not_found",
        )
    corpus = CorpusStore(settings.corpus_path)
    docs = corpus.get_resume_documents_by_snapshot_sha256(
        tenant_id=DEFAULT_TENANT_ID,
        workspace_id=user.workspace_id,
        snapshot_sha256_values=[candidate.snapshot_sha256],
    )
    doc = docs.get(candidate.snapshot_sha256)
    if doc is None:
        return WorkbenchGraphCandidateResumeSnapshotResponse(
            graphCandidateId=graph_candidate_id,
            status="snapshot_not_found",
            reason="snapshot_not_found",
        )
    if not _snapshot_materialization_allowed(doc):
        return WorkbenchGraphCandidateResumeSnapshotResponse(
            graphCandidateId=graph_candidate_id,
            status="snapshot_forbidden",
            reason="snapshot_forbidden",
        )
    return _project_doc(graph_candidate_id=graph_candidate_id, doc=doc, fallback=candidate.summary)


def _project_doc(
    *,
    graph_candidate_id: str,
    doc: dict[str, object],
    fallback: WorkbenchGraphCandidateSummaryResponse,
) -> WorkbenchGraphCandidateResumeSnapshotResponse:
    sections = _json_object(doc.get("normalized_sections_json"))
    profile = _json_object(sections.get("profile"))
    locations = _json_list(doc.get("locations_json"))
    display_name = _safe_text(profile.get("name"), 160) or _safe_text(fallback.displayName, 160) or ""
    headline = _safe_text(doc.get("current_title"), 160) or _safe_text(fallback.title, 160) or ""
    company = _safe_text(doc.get("current_company"), 160) or _safe_text(fallback.company, 160) or ""
    location = _safe_text(locations[0], 160) if locations else _safe_text(fallback.location, 160) or ""
    summary = _safe_text(profile.get("summary"), 500) or _safe_text(fallback.summary, 500) or ""
    return WorkbenchGraphCandidateResumeSnapshotResponse(
        graphCandidateId=graph_candidate_id,
        status="ready",
        profile=WorkbenchResumeSnapshotProfileResponse(
            displayName=display_name,
            headline=headline,
            company=company,
            location=location,
            summary=summary,
        ),
        workExperience=[
            WorkbenchResumeSnapshotWorkExperienceResponse(
                company=_safe_text(item.get("company"), 160) or "",
                title=_safe_text(item.get("title"), 160) or "",
                duration=_safe_text(item.get("duration"), 80),
                summary=_safe_text(item.get("summary"), 500),
            )
            for item in _dict_items(doc.get("experience_json"))[:20]
        ],
        education=[
            WorkbenchResumeSnapshotEducationResponse(
                school=_safe_text(item.get("school"), 160) or "",
                degree=_safe_text(item.get("degree"), 120),
                major=_safe_text(item.get("major"), 120),
            )
            for item in _dict_items(doc.get("education_json"))[:20]
        ],
        projects=[
            WorkbenchResumeSnapshotProjectResponse(
                name=_safe_text(item.get("name"), 160) or "",
                summary=_safe_text(item.get("summary"), 500),
            )
            for item in _dict_items(sections.get("projects"))[:20]
        ],
        skills=[skill for skill in (_safe_text(value, 80) for value in _json_list(doc.get("skills_json"))) if skill][:50],
        sourceEvidence=[
            WorkbenchResumeSnapshotSourceEvidenceResponse(label="summary", text=summary)
        ]
        if summary
        else [],
    )


def _dict_items(value: object) -> list[dict[str, object]]:
    return [item for item in _json_list(value) if isinstance(item, dict)]


def _json_object(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _json_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _snapshot_materialization_allowed(doc: dict[str, object]) -> bool:
    if not bool(doc.get("internal_materialization_eligible")):
        return False
    redaction_status = str(doc.get("redaction_status") or "").strip().casefold()
    if redaction_status in {"blocked", "forbidden", "failed"}:
        return False
    allowed_uses = {str(value).strip().casefold() for value in _json_list(doc.get("allowed_uses_json"))}
    return bool(allowed_uses.intersection({"search", "recruiting", "internal_materialization", "workspace_recruiting_record"}))


def _safe_text(value: object, max_length: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    forbidden = (
        "cookie",
        "authorization",
        "bearer ",
        "set-cookie",
        "authheader",
        "storagestate",
        "localstorage",
        "sessionstorage",
        "cdp",
        "websocket",
        "websocketdebuggerurl",
        "wsendpoint",
        "run_dir",
        "artifact",
        "provider_account_hash",
        "provider-secret",
        "source-secret",
        "token=",
        "ticket=",
    )
    lowered = text.lower()
    if any(token in lowered for token in forbidden):
        return None
    if "://" in lowered and ("http://" in lowered or "https://" in lowered or "ws://" in lowered or "wss://" in lowered):
        return None
    return text[:max_length]
