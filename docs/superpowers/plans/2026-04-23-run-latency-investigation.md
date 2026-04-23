# Run Latency Investigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small evidence-first latency audit path for whole `seektalent run` duration and record exact local validator retry reasons.

**Architecture:** Add one read-only tool that summarizes existing `runs/` artifacts without importing runtime internals. Add minimal retry-reason state to the controller and finalizer validators, then pass those reasons into existing LLM call snapshots. Do not change model selection, retry counts, retrieval behavior, scoring, ranking, or stop logic.

**Tech Stack:** Python, argparse, json, pathlib, datetime, Pydantic models, Pydantic AI validators, pytest, existing SeekTalent tracing artifacts.

---

## File Structure

- Create `tools/audit_run_latency.py`  
  Read one or more run directories and print a compact JSON latency report. The script depends only on artifact files and the Python standard library.
- Create `tests/test_run_latency_audit_tool.py`  
  Unit tests for the audit script using synthetic run artifact directories.
- Modify `src/seektalent/tracing.py`  
  Add `validator_retry_reasons` to `LLMCallSnapshot`.
- Modify `src/seektalent/controller/react_controller.py`  
  Track local controller validator retry reasons before each `ModelRetry`.
- Modify `src/seektalent/finalize/finalizer.py`  
  Track local finalizer validator retry reasons before each `ModelRetry`.
- Modify `src/seektalent/runtime/orchestrator.py`  
  Include retry reasons in controller and finalizer call snapshots.
- Modify `tests/test_controller_contract.py`  
  Assert controller retry reasons are recorded.
- Modify `tests/test_finalizer_contract.py`  
  Assert finalizer retry reasons are recorded.
- Modify `tests/test_runtime_audit.py`  
  Assert call snapshots include retry reason arrays.

---

## Task 1: Add Artifact-Only Latency Audit Tests

**Files:**
- Create: `tests/test_run_latency_audit_tool.py`

- [ ] **Step 1: Write failing tests for synthetic run summaries**

Create `tests/test_run_latency_audit_tool.py`:

```python
import json
from pathlib import Path

from tools.audit_run_latency import audit_run_dir


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_audit_run_dir_groups_stage_latency(tmp_path: Path) -> None:
    run_dir = tmp_path / "20260423_120000_abc12345"
    _write_jsonl(
        run_dir / "events.jsonl",
        [
            {"timestamp": "2026-04-23T12:00:00+08:00", "event_type": "run_started"},
            {
                "timestamp": "2026-04-23T12:00:10+08:00",
                "event_type": "requirements_completed",
                "latency_ms": 10_000,
            },
            {
                "timestamp": "2026-04-23T12:01:00+08:00",
                "event_type": "controller_completed",
                "round_no": 1,
                "latency_ms": 50_000,
            },
            {
                "timestamp": "2026-04-23T12:01:02+08:00",
                "event_type": "tool_succeeded",
                "round_no": 1,
                "latency_ms": 2_000,
            },
            {
                "timestamp": "2026-04-23T12:01:12+08:00",
                "event_type": "score_branch_completed",
                "round_no": 1,
                "latency_ms": 10_000,
            },
            {
                "timestamp": "2026-04-23T12:02:00+08:00",
                "event_type": "reflection_completed",
                "round_no": 1,
                "latency_ms": 48_000,
            },
            {
                "timestamp": "2026-04-23T12:02:30+08:00",
                "event_type": "finalizer_completed",
                "latency_ms": 30_000,
            },
            {
                "timestamp": "2026-04-23T12:02:31+08:00",
                "event_type": "run_finished",
                "stop_reason": "controller_stop",
            },
        ],
    )

    summary = audit_run_dir(run_dir)

    assert summary["run_dir"] == str(run_dir)
    assert summary["observed_wall_clock_ms"] == 151_000
    assert summary["stop_reason"] == "controller_stop"
    assert summary["rounds_observed"] == [1]
    assert summary["stages"]["requirements"]["total_ms"] == 10_000
    assert summary["stages"]["controller"]["total_ms"] == 50_000
    assert summary["stages"]["cts_tool"]["total_ms"] == 2_000
    assert summary["stages"]["scoring"]["total_ms"] == 10_000
    assert summary["stages"]["reflection"]["total_ms"] == 48_000
    assert summary["stages"]["finalizer"]["total_ms"] == 30_000
    assert summary["top_stage_by_recorded_latency"] == "controller"


def test_audit_run_dir_reads_retry_counts_from_call_snapshots(tmp_path: Path) -> None:
    run_dir = tmp_path / "20260423_120000_def67890"
    _write_jsonl(
        run_dir / "events.jsonl",
        [
            {"timestamp": "2026-04-23T12:00:00+08:00", "event_type": "run_started"},
            {"timestamp": "2026-04-23T12:01:00+08:00", "event_type": "run_finished"},
        ],
    )
    _write_json(
        run_dir / "rounds" / "round_04" / "controller_call.json",
        {
            "stage": "controller",
            "call_id": "controller-r04",
            "round_no": 4,
            "latency_ms": 154_898,
            "validator_retry_count": 1,
            "validator_retry_reasons": ["response_to_reflection is required when previous_reflection exists."],
            "prompt_chars": 4097,
            "input_payload_chars": 5497,
            "output_chars": 742,
        },
    )
    _write_json(
        run_dir / "finalizer_call.json",
        {
            "stage": "finalize",
            "call_id": "finalizer",
            "latency_ms": 38_359,
            "validator_retry_count": 0,
            "validator_retry_reasons": [],
            "prompt_chars": 1201,
            "input_payload_chars": 2688,
            "output_chars": 2360,
        },
    )

    summary = audit_run_dir(run_dir)

    assert summary["llm_calls"]["controller"]["retry_count"] == 1
    assert summary["llm_calls"]["controller"]["retry_reasons"] == [
        "response_to_reflection is required when previous_reflection exists."
    ]
    assert summary["llm_calls"]["controller"]["max_latency_ms"] == 154_898
    assert summary["llm_calls"]["finalize"]["retry_count"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_run_latency_audit_tool.py -v
```

Expected: fail with `ModuleNotFoundError: No module named 'tools.audit_run_latency'`.

- [ ] **Step 3: Commit the failing tests only if using strict TDD checkpointing**

For this repository, prefer waiting until Task 2 passes before committing.

---

## Task 2: Implement `tools/audit_run_latency.py`

**Files:**
- Create: `tools/audit_run_latency.py`
- Test: `tests/test_run_latency_audit_tool.py`

- [ ] **Step 1: Add the audit script**

Create `tools/audit_run_latency.py`:

```python
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


STAGE_EVENTS = {
    "requirements_completed": "requirements",
    "controller_completed": "controller",
    "reflection_completed": "reflection",
    "finalizer_completed": "finalizer",
    "score_branch_completed": "scoring",
    "tool_succeeded": "cts_tool",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _stage_bucket() -> dict[str, int]:
    return {"count": 0, "total_ms": 0, "max_ms": 0}


def _add_latency(bucket: dict[str, int], latency_ms: object) -> None:
    if not isinstance(latency_ms, int | float):
        return
    value = int(latency_ms)
    bucket["count"] += 1
    bucket["total_ms"] += value
    bucket["max_ms"] = max(bucket["max_ms"], value)


def _call_snapshot_paths(run_dir: Path) -> list[Path]:
    paths = [
        run_dir / "requirements_call.json",
        run_dir / "finalizer_call.json",
    ]
    rounds_dir = run_dir / "rounds"
    if rounds_dir.exists():
        for round_dir in sorted(rounds_dir.glob("round_*")):
            paths.extend(
                [
                    round_dir / "controller_call.json",
                    round_dir / "reflection_call.json",
                ]
            )
    return [path for path in paths if path.exists()]


def _scoring_snapshot_paths(run_dir: Path) -> list[Path]:
    rounds_dir = run_dir / "rounds"
    if not rounds_dir.exists():
        return []
    return sorted(rounds_dir.glob("round_*/scoring_calls.jsonl"))


def _empty_llm_bucket() -> dict[str, Any]:
    return {
        "count": 0,
        "total_latency_ms": 0,
        "max_latency_ms": 0,
        "retry_count": 0,
        "retry_reasons": [],
        "max_input_payload_chars": 0,
        "max_output_chars": 0,
    }


def _add_call(bucket: dict[str, Any], snapshot: dict[str, Any]) -> None:
    bucket["count"] += 1
    latency = int(snapshot.get("latency_ms") or 0)
    bucket["total_latency_ms"] += latency
    bucket["max_latency_ms"] = max(bucket["max_latency_ms"], latency)
    bucket["retry_count"] += int(snapshot.get("validator_retry_count") or 0)
    for reason in snapshot.get("validator_retry_reasons") or []:
        if reason not in bucket["retry_reasons"]:
            bucket["retry_reasons"].append(reason)
    bucket["max_input_payload_chars"] = max(
        bucket["max_input_payload_chars"],
        int(snapshot.get("input_payload_chars") or 0),
    )
    bucket["max_output_chars"] = max(
        bucket["max_output_chars"],
        int(snapshot.get("output_chars") or 0),
    )


def audit_run_dir(run_dir: Path) -> dict[str, Any]:
    events = _read_jsonl(run_dir / "events.jsonl")
    stages: dict[str, dict[str, int]] = defaultdict(_stage_bucket)
    rounds: set[int] = set()
    stop_reason: str | None = None
    timestamps = []

    for event in events:
        timestamp = _parse_timestamp(event.get("timestamp"))
        if timestamp is not None:
            timestamps.append(timestamp)
        if isinstance(event.get("round_no"), int):
            rounds.add(int(event["round_no"]))
        if event.get("stop_reason"):
            stop_reason = str(event["stop_reason"])
        stage = STAGE_EVENTS.get(str(event.get("event_type")))
        if stage is not None:
            _add_latency(stages[stage], event.get("latency_ms"))

    llm_calls: dict[str, dict[str, Any]] = defaultdict(_empty_llm_bucket)
    for path in _call_snapshot_paths(run_dir):
        snapshot = _read_json(path)
        stage = str(snapshot.get("stage") or "unknown")
        _add_call(llm_calls[stage], snapshot)
    for path in _scoring_snapshot_paths(run_dir):
        for snapshot in _read_jsonl(path):
            _add_call(llm_calls["scoring"], snapshot)

    top_stage = None
    if stages:
        top_stage = max(stages.items(), key=lambda item: item[1]["total_ms"])[0]

    observed_wall_clock_ms = None
    if len(timestamps) >= 2:
        observed_wall_clock_ms = int((max(timestamps) - min(timestamps)).total_seconds() * 1000)

    return {
        "run_dir": str(run_dir),
        "observed_wall_clock_ms": observed_wall_clock_ms,
        "stop_reason": stop_reason,
        "rounds_observed": sorted(rounds),
        "stages": dict(sorted(stages.items())),
        "top_stage_by_recorded_latency": top_stage,
        "llm_calls": dict(sorted(llm_calls.items())),
    }


def _discover_run_dirs(paths: list[Path]) -> list[Path]:
    run_dirs: list[Path] = []
    for path in paths:
        if (path / "events.jsonl").exists():
            run_dirs.append(path)
            continue
        run_dirs.extend(sorted(item for item in path.glob("*") if (item / "events.jsonl").exists()))
    return run_dirs


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize SeekTalent run latency from artifact files.")
    parser.add_argument("paths", nargs="*", default=["runs"], help="Run directories or roots containing run directories.")
    parser.add_argument("--limit", type=int, default=20, help="Only include the newest N discovered runs.")
    args = parser.parse_args()

    run_dirs = _discover_run_dirs([Path(path) for path in args.paths])
    selected = sorted(run_dirs, key=lambda path: path.stat().st_mtime)[-args.limit :]
    payload = {
        "run_count": len(selected),
        "runs": [audit_run_dir(path) for path in selected],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the new tests**

Run:

```bash
uv run pytest tests/test_run_latency_audit_tool.py -v
```

Expected: pass.

- [ ] **Step 3: Run the tool against recent local runs**

Run:

```bash
uv run python tools/audit_run_latency.py runs --limit 8 > /tmp/seektalent_run_latency_audit.json
```

Expected: `/tmp/seektalent_run_latency_audit.json` contains `run_count`, `runs`, stage totals, LLM retry counts, and retry reasons when present. Do not commit this `/tmp` output.

- [ ] **Step 4: Commit Task 1 and Task 2**

Run:

```bash
git add tools/audit_run_latency.py tests/test_run_latency_audit_tool.py
git commit -m "Add run latency audit tool"
```

---

## Task 3: Add Controller Retry Reason Tests

**Files:**
- Modify: `tests/test_controller_contract.py`

- [ ] **Step 1: Add failing assertions to existing validator tests**

In `tests/test_controller_contract.py`, update the existing tests that expect `ModelRetry` from the controller validator. After each `with pytest.raises(...)` block, assert the recorded reason.

For `test_controller_output_validator_rejects_missing_response_to_reflection`, add:

```python
    assert controller.last_validator_retry_reasons == [
        "response_to_reflection is required when previous_reflection exists."
    ]
```

For `test_controller_output_validator_rejects_empty_query_terms`, add:

```python
    assert controller.last_validator_retry_reasons == [
        "proposed_query_terms must contain at least one term."
    ]
```

For `test_controller_output_validator_rejects_blocked_compiler_terms`, add:

```python
    assert controller.last_validator_retry_reasons
    assert "compiler-admitted" in controller.last_validator_retry_reasons[0]
```

- [ ] **Step 2: Run failing controller tests**

Run:

```bash
uv run pytest \
  tests/test_controller_contract.py::test_controller_output_validator_rejects_missing_response_to_reflection \
  tests/test_controller_contract.py::test_controller_output_validator_rejects_empty_query_terms \
  tests/test_controller_contract.py::test_controller_output_validator_rejects_blocked_compiler_terms \
  -v
```

Expected: fail because `last_validator_retry_reasons` does not exist.

---

## Task 4: Implement Controller Retry Reason Tracking

**Files:**
- Modify: `src/seektalent/controller/react_controller.py`
- Test: `tests/test_controller_contract.py`

- [ ] **Step 1: Add retry reason state and helper**

In `ReActController.__init__`, add:

```python
        self.last_validator_retry_reasons: list[str] = []
```

Add this method to `ReActController`:

```python
    def _record_retry(self, reason: str) -> ModelRetry:
        self.last_validator_retry_count += 1
        self.last_validator_retry_reasons.append(reason)
        return ModelRetry(reason)
```

- [ ] **Step 2: Replace validator retry increments**

In `validate_output`, replace:

```python
                self.last_validator_retry_count += 1
                raise ModelRetry("proposed_query_terms must contain at least one term.")
```

with:

```python
                raise self._record_retry("proposed_query_terms must contain at least one term.")
```

Replace:

```python
                    self.last_validator_retry_count += 1
                    raise ModelRetry(str(exc)) from exc
```

with:

```python
                    raise self._record_retry(str(exc)) from exc
```

Replace:

```python
                self.last_validator_retry_count += 1
                raise ModelRetry("response_to_reflection is required when previous_reflection exists.")
```

with:

```python
                raise self._record_retry("response_to_reflection is required when previous_reflection exists.")
```

- [ ] **Step 3: Reset reasons for each controller call**

In `decide`, replace:

```python
        self.last_validator_retry_count = 0
```

with:

```python
        self.last_validator_retry_count = 0
        self.last_validator_retry_reasons = []
```

- [ ] **Step 4: Run controller tests**

Run:

```bash
uv run pytest \
  tests/test_controller_contract.py::test_controller_output_validator_rejects_missing_response_to_reflection \
  tests/test_controller_contract.py::test_controller_output_validator_rejects_empty_query_terms \
  tests/test_controller_contract.py::test_controller_output_validator_rejects_blocked_compiler_terms \
  -v
```

Expected: pass.

- [ ] **Step 5: Commit controller retry reason tracking**

Run:

```bash
git add src/seektalent/controller/react_controller.py tests/test_controller_contract.py
git commit -m "Record controller retry reasons"
```

---

## Task 5: Add Finalizer Retry Reason Tests and Tracking

**Files:**
- Modify: `tests/test_finalizer_contract.py`
- Modify: `src/seektalent/finalize/finalizer.py`

- [ ] **Step 1: Add failing assertions to finalizer validator tests**

In `tests/test_finalizer_contract.py`, update existing tests that expect finalizer `ModelRetry`.

For `test_finalizer_output_validator_rejects_duplicate_resume_ids`, add:

```python
    assert finalizer.last_validator_retry_reasons == [
        "Duplicate resume_id 'resume-1' in final candidates."
    ]
```

For `test_finalizer_output_validator_rejects_unknown_resume_ids`, add:

```python
    assert finalizer.last_validator_retry_reasons == [
        "Unknown resume_id 'unknown' in final candidates."
    ]
```

For `test_finalizer_output_validator_rejects_incomplete_shortlist`, add:

```python
    assert finalizer.last_validator_retry_reasons == [
        "Final candidates count must equal runtime top candidate count."
    ]
```

- [ ] **Step 2: Run failing finalizer tests**

Run:

```bash
uv run pytest \
  tests/test_finalizer_contract.py::test_finalizer_output_validator_rejects_duplicate_resume_ids \
  tests/test_finalizer_contract.py::test_finalizer_output_validator_rejects_unknown_resume_ids \
  tests/test_finalizer_contract.py::test_finalizer_output_validator_rejects_incomplete_shortlist \
  -v
```

Expected: fail because `last_validator_retry_reasons` does not exist.

- [ ] **Step 3: Add retry reason state and helper**

In `Finalizer.__init__`, add:

```python
        self.last_validator_retry_reasons: list[str] = []
```

Add this method to `Finalizer`:

```python
    def _record_retry(self, reason: str) -> ModelRetry:
        self.last_validator_retry_count += 1
        self.last_validator_retry_reasons.append(reason)
        return ModelRetry(reason)
```

- [ ] **Step 4: Replace finalizer validator retry increments**

In `validate_output`, replace each `self.last_validator_retry_count += 1` plus `raise ModelRetry(...)` pair with `raise self._record_retry(...)`.

Use these exact reason strings:

```python
f"Unknown resume_id {candidate.resume_id!r} in final candidates."
f"Duplicate resume_id {candidate.resume_id!r} in final candidates."
"Final candidates count must equal runtime top candidate count."
"Final candidates must preserve runtime ranking order."
```

- [ ] **Step 5: Reset reasons for each finalizer call**

In `finalize`, replace:

```python
        self.last_validator_retry_count = 0
```

with:

```python
        self.last_validator_retry_count = 0
        self.last_validator_retry_reasons = []
```

- [ ] **Step 6: Run finalizer tests**

Run:

```bash
uv run pytest \
  tests/test_finalizer_contract.py::test_finalizer_output_validator_rejects_duplicate_resume_ids \
  tests/test_finalizer_contract.py::test_finalizer_output_validator_rejects_unknown_resume_ids \
  tests/test_finalizer_contract.py::test_finalizer_output_validator_rejects_incomplete_shortlist \
  -v
```

Expected: pass.

- [ ] **Step 7: Commit finalizer retry reason tracking**

Run:

```bash
git add src/seektalent/finalize/finalizer.py tests/test_finalizer_contract.py
git commit -m "Record finalizer retry reasons"
```

---

## Task 6: Add Retry Reasons to LLM Call Snapshots

**Files:**
- Modify: `src/seektalent/tracing.py`
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `tests/test_runtime_audit.py`

- [ ] **Step 1: Add failing runtime audit assertion**

In `tests/test_runtime_audit.py`, find the test that reads `controller_call.json` and `finalizer_call.json`. Add assertions that both snapshots include `validator_retry_reasons`:

```python
    assert controller_call["validator_retry_reasons"] == []
    assert finalizer_call["validator_retry_reasons"] == []
```

If the current test uses a stub controller with retry count `0`, the expected reason list should be empty.

- [ ] **Step 2: Run failing audit test**

Run:

```bash
uv run pytest tests/test_runtime_audit.py::test_runtime_writes_v02_audit_outputs -v
```

Expected: fail because `validator_retry_reasons` is missing from snapshots.

- [ ] **Step 3: Extend `LLMCallSnapshot`**

In `src/seektalent/tracing.py`, add the field after `validator_retry_count`:

```python
    validator_retry_reasons: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Extend `_build_llm_call_snapshot`**

In `src/seektalent/runtime/orchestrator.py`, add a keyword parameter:

```python
        validator_retry_reasons: list[str] | None = None,
```

Pass it into `LLMCallSnapshot`:

```python
            validator_retry_reasons=validator_retry_reasons or [],
```

- [ ] **Step 5: Pass controller and finalizer reasons into snapshots**

For each controller snapshot call, add:

```python
                        validator_retry_reasons=self.controller.last_validator_retry_reasons,
```

For each finalizer snapshot call, add:

```python
                        validator_retry_reasons=self.finalizer.last_validator_retry_reasons,
```

Do this for success and failure snapshot paths.

- [ ] **Step 6: Run runtime audit test**

Run:

```bash
uv run pytest tests/test_runtime_audit.py::test_runtime_writes_v02_audit_outputs -v
```

Expected: pass.

- [ ] **Step 7: Run focused retry tests**

Run:

```bash
uv run pytest tests/test_controller_contract.py tests/test_finalizer_contract.py tests/test_runtime_audit.py::test_runtime_writes_v02_audit_outputs -q
```

Expected: pass.

- [ ] **Step 8: Commit snapshot retry reasons**

Run:

```bash
git add src/seektalent/tracing.py src/seektalent/runtime/orchestrator.py tests/test_runtime_audit.py
git commit -m "Write retry reasons to LLM call snapshots"
```

---

## Task 7: Execute the Read-Only Audit and Decide Next Experiment

**Files:**
- No source changes.
- Do not commit generated `/tmp` audit output.

- [ ] **Step 1: Run the audit on recent runs**

Run:

```bash
uv run python tools/audit_run_latency.py runs --limit 12 > /tmp/seektalent_run_latency_audit.json
```

Expected: command exits `0`.

- [ ] **Step 2: Inspect top contributors**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("/tmp/seektalent_run_latency_audit.json").read_text())
for run in payload["runs"]:
    stages = run["stages"]
    ranked = sorted(stages.items(), key=lambda item: item[1]["total_ms"], reverse=True)
    print(run["run_dir"])
    print("  wall_clock_ms:", run["observed_wall_clock_ms"])
    for name, data in ranked[:3]:
        print(" ", name, data)
    for stage, data in run["llm_calls"].items():
        if data["retry_count"]:
            print("  retry", stage, data["retry_count"], data["retry_reasons"])
PY
```

Expected: printed output identifies the top three recorded latency stages per run and any retry reasons already present in newly instrumented runs.

- [ ] **Step 3: If controller/reflection dominate, run thinking A/B manually**

Use the same JD and notes for all variants. Keep outputs under `/tmp` or a dated `runs/latency_ab_*` root.

Baseline:

```bash
SEEKTALENT_ENABLE_EVAL=false \
seektalent run --env-file .env --job-title "Python agent engineer" --jd "Python agent engineer with retrieval and ranking experience" --json
```

Controller off:

```bash
SEEKTALENT_CONTROLLER_ENABLE_THINKING=false \
SEEKTALENT_ENABLE_EVAL=false \
seektalent run --env-file .env --job-title "Python agent engineer" --jd "Python agent engineer with retrieval and ranking experience" --json
```

Reflection off:

```bash
SEEKTALENT_REFLECTION_ENABLE_THINKING=false \
SEEKTALENT_ENABLE_EVAL=false \
seektalent run --env-file .env --job-title "Python agent engineer" --jd "Python agent engineer with retrieval and ranking experience" --json
```

Both off:

```bash
SEEKTALENT_CONTROLLER_ENABLE_THINKING=false \
SEEKTALENT_REFLECTION_ENABLE_THINKING=false \
SEEKTALENT_ENABLE_EVAL=false \
seektalent run --env-file .env --job-title "Python agent engineer" --jd "Python agent engineer with retrieval and ranking experience" --json
```

Expected: each successful run writes a new run directory. Re-run `tools/audit_run_latency.py` against those run directories to compare controller/reflection latency and retries.

- [ ] **Step 4: Report evidence before proposing a behavior change**

Report:

```text
- Top wall-clock contributors:
- Retry reasons found:
- Thinking A/B latency delta:
- Whether a behavior/config change is justified:
```

Do not disable thinking by default until the evidence report exists.

---

## Final Verification

- [ ] Run:

```bash
uv run pytest tests/test_run_latency_audit_tool.py tests/test_controller_contract.py tests/test_finalizer_contract.py tests/test_runtime_audit.py::test_runtime_writes_v02_audit_outputs -q
```

Expected: pass.

- [ ] Run:

```bash
uv run python tools/audit_run_latency.py runs --limit 3 > /tmp/seektalent_run_latency_audit_smoke.json
```

Expected: pass and writes valid JSON.

- [ ] Run:

```bash
git status --short
```

Expected: only intended tracked source/test changes remain before final commit; generated `/tmp` files do not appear.

## Self-Review

- Spec coverage: Tasks 1-2 cover artifact-only latency audit. Tasks 3-6 cover retry reason attribution. Task 7 covers the read-only audit execution and the same-JD thinking A/B decision gate.
- Scope check: The plan does not change retrieval, scoring, ranking, stop logic, model ids, or retry counts.
- Marker scan: No deferred-work markers are present.
- Type consistency: `validator_retry_reasons` is a `list[str]` in snapshots and local agent state.
