import asyncio

import pytest

from seektalent.core.retrieval.provider_contract import SearchRequest
from seektalent.models import ResumeCandidate
from seektalent.providers.cts import CTSProviderAdapter
from seektalent.providers.cts.mapper import build_provider_candidate
from tests.settings_factory import make_settings


def test_cts_candidate_mapper_builds_resume_candidate() -> None:
    candidate = ResumeCandidate(
        resume_id="resume-1",
        source_resume_id="source-1",
        snapshot_sha256="snap",
        dedup_key="resume-1",
        search_text="python engineer",
        raw={"resumeId": "resume-1"},
    )

    mapped = build_provider_candidate(candidate)

    assert mapped.resume_id == "resume-1"
    assert mapped.dedup_key == "resume-1"


def test_cts_candidate_mapper_isolates_mutable_fields() -> None:
    candidate = ResumeCandidate(
        resume_id="resume-1",
        source_resume_id="source-1",
        snapshot_sha256="snap",
        dedup_key="resume-1",
        education_summaries=["BS Computer Science"],
        work_experience_summaries=["Built matching systems"],
        search_text="python engineer",
        raw={"resumeId": "resume-1", "tags": ["python"]},
    )

    mapped = build_provider_candidate(candidate)
    mapped.raw["resumeId"] = "resume-2"
    mapped.raw["tags"].append("ml")
    mapped.education_summaries.append("MS AI")
    mapped.work_experience_summaries.append("Led search infra")

    assert candidate.raw == {"resumeId": "resume-1", "tags": ["python"]}
    assert candidate.education_summaries == ["BS Computer Science"]
    assert candidate.work_experience_summaries == ["Built matching systems"]


def test_cts_provider_adapter_searches_summary_results() -> None:
    provider = CTSProviderAdapter(make_settings(mock_cts=True))
    request = SearchRequest(
        query_terms=["python"],
        query_role="primary",
        runtime_constraints=[],
        fetch_mode="summary",
        page_size=1,
    )

    result = asyncio.run(provider.search(request, round_no=1, trace_id="trace-1"))

    assert provider.name == "cts"
    capabilities = provider.describe_capabilities()
    assert capabilities.supports_fetch_mode_summary is True
    assert capabilities.supports_fetch_mode_detail is False
    assert result.candidates
    assert result.candidates[0].source_round == 1
    assert result.next_cursor == "2"
    assert result.exhausted is False
    assert any("CTS query_role exploit" in note for note in result.diagnostics)


def test_cts_provider_adapter_rejects_detail_fetch_mode() -> None:
    provider = CTSProviderAdapter(make_settings(mock_cts=True))
    request = SearchRequest(
        query_terms=["python"],
        query_role="primary",
        runtime_constraints=[],
        fetch_mode="detail",
        page_size=10,
    )

    with pytest.raises(ValueError, match="does not support fetch_mode=detail"):
        asyncio.run(provider.search(request, round_no=1, trace_id="trace-1"))
