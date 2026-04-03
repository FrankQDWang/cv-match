import asyncio

from deepmatch.clients.cts_client import MockCTSClient
from deepmatch.config import AppSettings
from deepmatch.models import CTSQuery, ResumeCandidate
from deepmatch.normalization import normalize_resume


def test_normalize_resume_keeps_exact_location_text() -> None:
    candidate = ResumeCandidate(
        resume_id="r-1",
        dedup_key="r-1",
        now_location=" 上海 ",
        expected_location="上海",
        expected_job_category="Python Engineer",
        search_text="python engineer",
        raw={},
    )

    normalized = normalize_resume(candidate)

    assert normalized.locations == ["上海"]


def test_mock_cts_matches_exact_location_filter() -> None:
    client = MockCTSClient(AppSettings(_env_file=None))
    query = CTSQuery(
        query_terms=["python", "agent"],
        keyword_query="python agent",
        native_filters={"location": ["上海"]},
        rationale="test exact location filter",
    )

    result = asyncio.run(client.search(query, round_no=1, trace_id="trace-1"))

    assert result.candidates
    assert all(candidate.now_location == "上海" for candidate in result.candidates)
