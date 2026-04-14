from __future__ import annotations

import asyncio
import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

from seektalent.config import AppSettings
from seektalent.evaluation import JudgeCache, ResumeJudgeResult, evaluate_run, ndcg_at_10, precision_at_10, snapshot_sha256
from seektalent.models import ResumeCandidate
from seektalent.prompting import LoadedPrompt


def test_snapshot_sha256_is_stable_for_key_order() -> None:
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}

    assert snapshot_sha256(left) == snapshot_sha256(right)


def test_ndcg_at_10_is_one_for_ideal_ranking() -> None:
    assert ndcg_at_10([3, 2, 2, 1, 0]) == 1.0


def test_precision_at_10_counts_scores_two_and_above() -> None:
    assert precision_at_10([3, 2, 1, 0]) == 0.2


def test_judge_cache_round_trip(tmp_path: Path) -> None:
    cache = JudgeCache(tmp_path)
    try:
        result = ResumeJudgeResult(score=3, rationale="Strong direct match.")
        cache.put(
            jd_sha256_value="jd",
            snapshot_sha256_value="resume",
            model_id="openai-chat:deepseek-v3.2",
            result=result,
        )

        loaded = cache.get(
            jd_sha256_value="jd",
            snapshot_sha256_value="resume",
            model_id="openai-chat:deepseek-v3.2",
        )

        assert loaded == result
    finally:
        cache.close()


def test_evaluate_run_keeps_no_judge_artifacts_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_judge_many(self, *, jd, candidates, cache):  # noqa: ANN001
        del self, jd, candidates, cache
        raise RuntimeError("judge failed")

    monkeypatch.setattr("seektalent.evaluation.ResumeJudge.judge_many", fake_judge_many)
    settings = AppSettings(_env_file=None, runs_dir=str(tmp_path / "runs"))
    prompt = LoadedPrompt(name="judge", path=tmp_path / "judge.md", content="judge prompt", sha256="hash")
    candidate = ResumeCandidate(
        resume_id="resume-1",
        source_resume_id="resume-1",
        snapshot_sha256="snapshot-1",
        dedup_key="resume-1",
        expected_job_category="Engineer",
        now_location="上海",
        work_year=5,
        search_text="engineer",
        raw={"resume_id": "resume-1"},
    )
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    with pytest.raises(RuntimeError, match="judge failed"):
        asyncio.run(
            evaluate_run(
                settings=settings,
                prompt=prompt,
                run_id="run-1",
                run_dir=run_dir,
                jd="test jd",
                round_01_candidates=[candidate],
                final_candidates=[candidate],
            )
        )

    assert not (run_dir / "evaluation").exists()
    assert not (run_dir / "raw_resumes").exists()
    assert not (tmp_path / ".seektalent" / "judge_cache.sqlite3").exists()


def test_evaluate_run_logs_weave_and_updates_version_averages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    class FakePrediction:
        def __init__(self, inputs: dict, output: dict) -> None:
            self.inputs = inputs
            self.output = output
            self.scores: dict[str, object] = {}

        def log_score(self, name: str, value: object) -> None:
            self.scores[name] = value

        def finish(self) -> None:
            return None

    class FakeEvaluationLogger:
        instances: list["FakeEvaluationLogger"] = []

        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            self.kwargs = kwargs
            self.predictions: list[FakePrediction] = []
            self.views: dict[str, str] = {}
            self.summary: dict | None = None
            self.auto_summarize: bool | None = None
            type(self).instances.append(self)

        def log_prediction(self, *, inputs: dict, output: dict) -> FakePrediction:
            prediction = FakePrediction(inputs, output)
            self.predictions.append(prediction)
            return prediction

        def set_view(self, name: str, content: str, **kwargs) -> None:  # noqa: ANN003
            del kwargs
            self.views[name] = content

        def log_summary(self, summary: dict | None = None, auto_summarize: bool = True) -> None:
            self.summary = summary
            self.auto_summarize = auto_summarize

    init_calls: list[str] = []

    def fake_init(project_name: str):  # noqa: ANN001
        init_calls.append(project_name)
        return object()

    monkeypatch.setitem(
        sys.modules,
        "weave",
        SimpleNamespace(init=fake_init, EvaluationLogger=FakeEvaluationLogger),
    )

    async def fake_judge_many(self, *, jd, candidates, cache):  # noqa: ANN001
        del self, jd, cache
        result = ResumeJudgeResult(score=3, rationale="Strong fit")
        return (
            {candidate.resume_id: (result, False, 1) for candidate in candidates},
            [("jd", candidate.snapshot_sha256, "openai-responses:gpt-5.4", result) for candidate in candidates],
        )

    monkeypatch.setattr("seektalent.evaluation.ResumeJudge.judge_many", fake_judge_many)
    settings = AppSettings(
        _env_file=None,
        runs_dir=str(tmp_path / "runs"),
        weave_entity="frankqdwang1-personal-creations",
        weave_project="seektalent",
        judge_model="openai-responses:gpt-5.4",
    )
    prompt = LoadedPrompt(name="judge", path=tmp_path / "judge.md", content="judge prompt", sha256="hash")
    candidate = ResumeCandidate(
        resume_id="resume-1",
        source_resume_id="resume-1",
        snapshot_sha256="snapshot-1",
        dedup_key="resume-1",
        expected_job_category="Engineer",
        now_location="上海",
        work_year=5,
        search_text="engineer",
        raw={"resume_id": "resume-1"},
    )

    first_run_dir = tmp_path / "run-1"
    first_run_dir.mkdir()
    asyncio.run(
        evaluate_run(
            settings=settings,
            prompt=prompt,
            run_id="run-1",
            run_dir=first_run_dir,
            jd="test jd",
            round_01_candidates=[candidate],
            final_candidates=[candidate],
        )
    )
    first_averages = json.loads((first_run_dir / "evaluation" / "version_averages.json").read_text(encoding="utf-8"))

    second_run_dir = tmp_path / "run-2"
    second_run_dir.mkdir()
    asyncio.run(
        evaluate_run(
            settings=settings,
            prompt=prompt,
            run_id="run-2",
            run_dir=second_run_dir,
            jd="test jd",
            round_01_candidates=[candidate],
            final_candidates=[candidate],
        )
    )
    second_averages = json.loads((second_run_dir / "evaluation" / "version_averages.json").read_text(encoding="utf-8"))

    assert init_calls == [
        "frankqdwang1-personal-creations/seektalent",
        "frankqdwang1-personal-creations/seektalent",
    ]
    assert len(FakeEvaluationLogger.instances) == 4
    assert FakeEvaluationLogger.instances[0].summary == {
        "ndcg_at_10": 1.0,
        "precision_at_10": 0.1,
        "total_score": 0.37,
    }
    assert FakeEvaluationLogger.instances[0].auto_summarize is False
    assert "Version Mean" in FakeEvaluationLogger.instances[0].views["summary"]
    assert first_averages["round_01"]["count"] == 1
    assert first_averages["final"]["count"] == 1
    assert second_averages["round_01"]["count"] == 2
    assert second_averages["final"]["count"] == 2
