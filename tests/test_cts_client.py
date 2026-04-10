from __future__ import annotations

import asyncio

from seektalent.clients.cts_client import CTSClient, MockCTSClient
from seektalent.clients.cts_models import Candidate
from seektalent.config import AppSettings
from seektalent.models import ChildFrontierNodeStub, HardConstraints, RuntimeOnlyConstraints, SearchExecutionPlan_t


def _plan() -> SearchExecutionPlan_t:
    return SearchExecutionPlan_t(
        query_terms=["python", "agent workflow"],
        projected_filters=HardConstraints(
            locations=["上海"],
            company_names=["Hewa Talent Cloud"],
            degree_requirement="本科及以上",
            school_type_requirement=["211"],
            min_years=3,
            max_years=8,
        ),
        runtime_only_constraints=RuntimeOnlyConstraints(),
        target_new_candidate_count=2,
        semantic_hash="hash-1",
        knowledge_pack_ids=["llm_agent_rag_engineering"],
        child_frontier_node_stub=ChildFrontierNodeStub(
            frontier_node_id="node-1",
            parent_frontier_node_id="root",
            selected_operator_name="must_have_alias",
        ),
        derived_position="Python Agent Engineer",
        derived_work_content="retrieval ranking workflow",
    )


def test_cts_client_build_request_payload_uses_phase1_contract() -> None:
    client = CTSClient(AppSettings(_env_file=None, mock_cts=True))
    payload, notes = client.build_request_payload(_plan())

    assert payload["keyword"] == 'python "agent workflow"'
    assert payload["page"] == 1
    assert payload["pageSize"] == 2
    assert payload["location"] == "上海"
    assert payload["company"] == "Hewa Talent Cloud"
    assert payload["position"] == "Python Agent Engineer"
    assert payload["workContent"] == "retrieval ranking workflow"
    assert payload["degree"] == 2
    assert payload["schoolType"] == 2
    assert payload["workExperienceRange"] == 4
    assert any("degree_requirement mapped to CTS code 2" in note for note in notes)


def test_mock_cts_client_returns_retrieved_candidates() -> None:
    client = MockCTSClient(AppSettings(_env_file=None, mock_cts=True))
    plan = _plan()
    plan.derived_work_content = "retrieval ranking"
    result = asyncio.run(client.search(plan, trace_id="trace-1"))

    assert result.request_payload["position"] == "Python Agent Engineer"
    assert result.raw_candidate_count == len(result.candidates)
    assert result.candidates
    assert all(candidate.candidate_id.startswith("mock-r") for candidate in result.candidates)
    assert result.candidates[0].now_location == "上海"


def test_cts_client_normalizes_candidate_search_text_into_sections() -> None:
    client = CTSClient(AppSettings(_env_file=None, mock_cts=True))
    candidate = Candidate.model_validate(
        {
            "resume_id": "resume-1",
            "age": 30,
            "gender": "男",
            "expectedJobCategory": "Python Agent Engineer",
            "expectedIndustry": "AI Infra",
            "expectedLocation": "上海",
            "nowLocation": "杭州",
            "projectNameAll": ["retrieval platform"],
            "workSummariesAll": ["python backend", "ranking"],
            "workYear": 6,
            "educationList": [
                {"school": "复旦大学", "speciality": "计算机", "degree": "本科"}
            ],
            "workExperienceList": [
                {
                    "company": "TestCo",
                    "title": "Senior Engineer",
                    "summary": "Built ranking workflows",
                }
            ],
        }
    )

    normalized = client._normalize_candidate(candidate)

    assert normalized.search_text == (
        "Target role: Python Agent Engineer. "
        "Industry: AI Infra. "
        "Location: 上海, 杭州. "
        "Projects: retrieval platform. "
        "Work summary: python backend, ranking. "
        "Experience: TestCo | Senior Engineer | Built ranking workflows. "
        "Education: 复旦大学 计算机 本科."
    )
