import json
from pathlib import Path

from cv_match.clients.cts_client import CTSClientProtocol, CTSFetchResult
from cv_match.config import AppSettings
from cv_match.models import CTSQuery, ResumeCandidate
from cv_match.runtime import WorkflowRuntime
from cv_match.tracing import RunTracer


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[object]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def _make_candidate(resume_id: str, *, location: str = "上海") -> ResumeCandidate:
    return ResumeCandidate(
        resume_id=resume_id,
        dedup_key=resume_id,
        now_location=location,
        expected_location=location,
        expected_job_category="Python Engineer",
        work_year=6,
        education_summaries=["复旦大学 计算机 本科"],
        work_experience_summaries=["Example Co | Python Engineer | Built retrieval and tracing workflows."],
        project_names=["Resume search"],
        work_summaries=["python", "retrieval", "trace"],
        search_text="python retrieval trace resume search",
        raw={"resume_id": resume_id, "candidate_name": resume_id},
    )


class DuplicatePagingCTS(CTSClientProtocol):
    def search(self, query: CTSQuery, *, round_no: int, trace_id: str) -> CTSFetchResult:
        del round_no, trace_id
        if query.page == 1:
            candidates = [_make_candidate("dup-1"), _make_candidate("dup-1")]
        elif query.page == 2:
            candidates = [_make_candidate("uniq-2")]
        else:
            candidates = []
        return CTSFetchResult(
            request_payload={"page": query.page, "pageSize": query.page_size},
            candidates=candidates,
            raw_candidate_count=len(candidates),
            adapter_notes=[f"served page {query.page}"],
            latency_ms=1,
            response_message="ok",
        )


def test_execute_search_tool_refills_after_batch_dedup(tmp_path: Path) -> None:
    settings = AppSettings().with_overrides(
        runs_dir=str(tmp_path / "runs"),
        mock_cts=True,
        search_max_pages_per_round=3,
        search_max_attempts_per_round=3,
        search_no_progress_limit=2,
    )
    runtime = WorkflowRuntime(settings)
    runtime.cts_client = DuplicatePagingCTS()
    tracer = RunTracer(tmp_path / "trace-runs")
    query = CTSQuery(
        keywords=["python", "retrieval"],
        keyword_query="python retrieval",
        page=1,
        page_size=2,
        rationale="test refill after dedup",
    )

    try:
        new_candidates, observation, attempts, duplicate_count = runtime._execute_search_tool(
            round_no=1,
            query=query,
            target_new=2,
            seen_resume_ids=set(),
            seen_dedup_keys=set(),
            tracer=tracer,
        )
    finally:
        tracer.close()

    assert [candidate.resume_id for candidate in new_candidates] == ["dup-1", "uniq-2"]
    assert duplicate_count == 1
    assert len(attempts) == 2
    assert attempts[0].batch_duplicate_count == 1
    assert attempts[0].batch_unique_new_count == 1
    assert attempts[0].continue_refill is True
    assert attempts[1].cumulative_unique_new_count == 2
    assert observation.unique_new_count == 2
    assert observation.shortage_count == 0
    assert observation.new_resume_ids == ["dup-1", "uniq-2"]


def test_mock_runtime_writes_compact_audit_and_sanitized_outputs(tmp_path: Path) -> None:
    settings = AppSettings().with_overrides(
        runs_dir=str(tmp_path / "runs"),
        mock_cts=True,
        min_rounds=1,
        max_rounds=1,
        cts_tenant_key="tenant-key",
        cts_tenant_secret="tenant-secret",
    )
    runtime = WorkflowRuntime(settings)
    jd = (Path.cwd() / "examples" / "jd.md").read_text(encoding="utf-8")
    notes = (Path.cwd() / "examples" / "notes.md").read_text(encoding="utf-8")

    artifacts = runtime.run(jd=jd, notes=notes)

    round_dir = artifacts.run_dir / "rounds" / "round_01"
    react_step = _read_json(round_dir / "react_step.json")
    search_observation = _read_json(round_dir / "search_observation.json")
    scorecards = _read_jsonl(round_dir / "scorecards.jsonl")
    run_config = _read_json(artifacts.run_dir / "run_config.json")
    final_candidates = _read_json(artifacts.run_dir / "final_candidates.json")
    round_review = (round_dir / "round_review.md").read_text(encoding="utf-8")

    state_view = react_step["state_view"]
    assert "jd_summary" in state_view
    assert "notes_summary" in state_view
    assert "jd" not in state_view
    assert "notes" not in state_view

    assert len(search_observation["new_resume_ids"]) == len(set(search_observation["new_resume_ids"]))
    assert search_observation["new_resume_ids"].count("mock-r003") == 1

    scorecard_ids = [item["resume_id"] for item in scorecards]
    assert len(scorecard_ids) == len(set(scorecard_ids))
    assert scorecard_ids.count("mock-r003") == 1

    query_fields = {
        item["field"]
        for item in react_step["controller_decision"]["cts_query"]["hard_filters"]
        + react_step["controller_decision"]["cts_query"]["soft_filters"]
    }
    assert query_fields <= {"company", "position", "school", "work_content", "location"}

    assert "Search Outcome" in round_review
    assert "Top Pool Delta" in round_review
    assert "Common Drop Reasons" in round_review
    assert "Scoring Failures" in round_review
    assert "Reflection & Stop Signal" in round_review

    assert not (artifacts.run_dir / "round_summaries.json").exists()
    assert "cts_tenant_secret" not in json.dumps(run_config, ensure_ascii=False)
    assert "tenant-secret" not in json.dumps(run_config, ensure_ascii=False)
    assert final_candidates["summary"]
    assert all(candidate["match_summary"] for candidate in final_candidates["candidates"])

    source_python = "\n".join(path.read_text(encoding="utf-8") for path in Path("src").rglob("*.py"))
    readme = Path("README.md").read_text(encoding="utf-8")
    prompt_text = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/cv_match/prompts").glob("*.md"))
    assert "cv_match.agent" not in source_python
    assert "MatchRunner" not in source_python
    assert "├── agent/" not in readme
    assert "scoring agent" not in prompt_text.casefold()
    assert "reflection agent" not in prompt_text.casefold()
    assert "finalization agent" not in prompt_text.casefold()
