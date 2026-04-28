from __future__ import annotations

from pathlib import Path

from .models import LogicalArtifactEntry

STATIC_ENTRY_PATHS: dict[str, str] = {
    "runtime.trace_log": "trace.log",
    "runtime.events": "events.jsonl",
    "runtime.run_config": "run_config.json",
    "runtime.sent_query_history": "sent_query_history.json",
    "runtime.search_diagnostics": "search_diagnostics.json",
    "runtime.term_surface_audit": "term_surface_audit.json",
    "input.input_snapshot": "input_snapshot.json",
    "input.input_truth": "input_truth.json",
    "output.final_candidates": "final_candidates.json",
    "output.run_summary": "run_summary.md",
    "output.judge_packet": "judge_packet.json",
    "output.summary": "summary.json",
    "evaluation.evaluation": "evaluation/evaluation.json",
    "evaluation.replay_rows": "evaluation/replay_rows.jsonl",
}

ROUND_ENTRY_FILENAMES: dict[str, str] = {
    "query_resume_hits": "query_resume_hits.json",
    "replay_snapshot": "replay_snapshot.json",
    "second_lane_decision": "second_lane_decision.json",
    "prf_policy_decision": "prf_policy_decision.json",
    "controller_decision": "controller_decision.json",
    "controller_context": "controller_context.json",
    "reflection_advice": "reflection_advice.json",
    "reflection_call": "reflection_call.json",
    "scorecards": "scorecards.jsonl",
    "scoring_calls": "scoring_calls.jsonl",
    "scoring_input_refs": "scoring_input_refs.jsonl",
}

STATIC_ENTRIES: dict[str, LogicalArtifactEntry] = {
    name: LogicalArtifactEntry(name=name, relative_path=relative_path)
    for name, relative_path in STATIC_ENTRY_PATHS.items()
}


def default_logical_artifacts() -> dict[str, LogicalArtifactEntry]:
    return {
        name: entry.model_copy(deep=True)
        for name, entry in STATIC_ENTRIES.items()
    }


def resolve_registered_descriptor(
    descriptor: str,
    *,
    round_no: int | None = None,
) -> LogicalArtifactEntry | None:
    if descriptor in STATIC_ENTRIES:
        return STATIC_ENTRIES[descriptor].model_copy(deep=True)
    if descriptor.startswith("round."):
        round_key = descriptor.removeprefix("round.")
        return _round_entry(round_key, round_no=round_no)
    if descriptor.startswith("asset.prompt."):
        prompt_name = descriptor.removeprefix("asset.prompt.")
        return _prompt_entry(prompt_name)
    return None


def _round_entry(round_key: str, *, round_no: int | None) -> LogicalArtifactEntry:
    if round_no is None or round_no < 1:
        raise ValueError("Round descriptor resolution requires round_no >= 1.")
    filename = ROUND_ENTRY_FILENAMES.get(round_key)
    if filename is None:
        raise KeyError(f"Unknown round artifact descriptor: {round_key}")
    relative_path = Path("rounds") / f"round_{round_no:02d}" / filename
    return LogicalArtifactEntry(name=f"round.{round_key}", relative_path=relative_path.as_posix())


def _prompt_entry(prompt_name: str) -> LogicalArtifactEntry:
    clean_name = prompt_name.strip()
    if not clean_name or "/" in clean_name or "\\" in clean_name:
        raise ValueError("Prompt descriptor names must be simple file-safe names.")
    relative_path = Path("prompt_snapshots") / f"{clean_name}.md"
    return LogicalArtifactEntry(name=f"asset.prompt.{clean_name}", relative_path=relative_path.as_posix())
