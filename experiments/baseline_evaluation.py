from __future__ import annotations

import json
import shutil
from hashlib import sha256
from pathlib import Path

from seektalent.config import AppSettings
from seektalent.evaluation import (
    JUDGE_POLICY_VERSION,
    TOP_K,
    EvaluationArtifacts,
    EvaluationResult,
    ResumeJudge,
    _register_evaluation_outputs,
    _remove_path,
    _stage_result,
    export_replay_rows,
    export_judge_tasks,
    persist_raw_resume_snapshot,
)
from seektalent.flywheel.store import FLYWHEEL_LABEL_SCHEMA_VERSION, FlywheelStore
from seektalent.models import ResumeCandidate
from seektalent.prompting import LoadedPrompt
from seektalent.resumes.snapshots import snapshot_sha256


async def evaluate_baseline_run(
    *,
    settings: AppSettings,
    prompt: LoadedPrompt,
    run_id: str,
    run_dir: Path,
    jd: str,
    notes: str,
    round_01_candidates: list[ResumeCandidate],
    final_candidates: list[ResumeCandidate],
) -> EvaluationArtifacts:
    store = FlywheelStore(settings.flywheel_path)
    temp_root = run_dir / "._evaluation_tmp"
    final_evaluation_dir = run_dir / "evaluation"
    final_raw_dir = run_dir / "raw_resumes"
    try:
        jd_hash = sha256(jd.encode("utf-8")).hexdigest()
        unique_candidates: dict[str, ResumeCandidate] = {}
        for candidate in [*round_01_candidates[:TOP_K], *final_candidates[:TOP_K]]:
            unique_candidates[candidate.resume_id] = candidate
        task_id = store.upsert_task(job_title="", jd_text=jd, notes_text=notes)
        for candidate in unique_candidates.values():
            snapshot_hash = candidate.snapshot_sha256 or snapshot_sha256(candidate.raw)
            store.upsert_resume_snapshot(
                snapshot_sha256=snapshot_hash,
                source_resume_id=candidate.source_resume_id or candidate.resume_id,
                dedup_key=candidate.dedup_key,
                raw_payload=candidate.raw,
                normalized_preview={"search_text": candidate.search_text},
            )

        judged, pending_cache_writes = await ResumeJudge(settings, prompt).judge_many(
            task_id=task_id,
            jd=jd,
            notes=notes,
            candidates=list(unique_candidates.values()),
            store=store,
        )
        evaluation = EvaluationResult(
            run_id=run_id,
            judge_model=settings.effective_judge_model,
            jd_sha256=jd_hash,
            round_01=_stage_result(stage="round_01", candidates=round_01_candidates, judged=judged),
            final=_stage_result(stage="final", candidates=final_candidates, judged=judged),
        )
        _remove_path(temp_root)
        export_judge_tasks(run_dir=temp_root, stage="round_01", jd_sha256_value=jd_hash, candidates=round_01_candidates)
        export_judge_tasks(run_dir=temp_root, stage="final", jd_sha256_value=jd_hash, candidates=final_candidates)
        (temp_root / "raw_resumes").mkdir(parents=True, exist_ok=True)
        for candidate in unique_candidates.values():
            persist_raw_resume_snapshot(run_dir=temp_root, candidate=candidate)

        path = temp_root / "evaluation" / "evaluation.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(evaluation.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
        export_replay_rows(run_dir=run_dir, output_dir=temp_root / "evaluation")

        _remove_path(final_evaluation_dir)
        _remove_path(final_raw_dir)
        shutil.move(str(temp_root / "evaluation"), str(final_evaluation_dir))
        shutil.move(str(temp_root / "raw_resumes"), str(final_raw_dir))
        for write in pending_cache_writes:
            store.record_judge_label(
                task_id=write.task_id,
                snapshot_sha256=write.snapshot_sha256,
                judge_model_id=write.judge_model_id,
                judge_protocol_family=write.judge_protocol_family,
                judge_provider_label=write.judge_provider_label,
                judge_endpoint_kind=write.judge_endpoint_kind,
                structured_output_mode=write.structured_output_mode,
                judge_prompt_hash=write.judge_prompt_hash,
                judge_contract_hash=write.judge_contract_hash,
                judge_policy_version=JUDGE_POLICY_VERSION,
                label_schema_version=FLYWHEEL_LABEL_SCHEMA_VERSION,
                judge_output_schema_hash=write.judge_output_schema_hash,
                reasoning_effort=write.reasoning_effort,
                temperature=write.temperature,
                score=write.result.score,
                rationale=write.result.rationale,
                label_payload=write.result.model_dump(mode="json"),
                judge_prompt_text=write.judge_prompt_text,
                latency_ms=write.latency_ms,
            )
        _register_evaluation_outputs(run_dir, evaluation)
        _remove_path(temp_root)
        return EvaluationArtifacts(result=evaluation, path=final_evaluation_dir / "evaluation.json")
    except Exception:
        _remove_path(temp_root)
        _remove_path(final_evaluation_dir)
        _remove_path(final_raw_dir)
        raise
    finally:
        store.close()
