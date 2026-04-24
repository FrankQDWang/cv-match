# Benchmark Queue Design

## Context

`seektalent benchmark` currently runs rows from one JSONL file. It can run rows in parallel with `--benchmark-max-concurrency`, but eval side effects still happen inside each run. When eval is enabled, each run creates its own judge concurrency limiter and calls Weave/W&B directly. With multiple benchmark rows running at once, process-level judge concurrency can exceed the intended limit and W&B/Weave can run concurrently.

The benchmark inputs are maintained as domain JSONL files under `artifacts/benchmarks/`. The generated combined file `phase_2_2_pilot.jsonl` should not be a required maintenance target.

## Goals

- Run all maintained benchmark JD rows from domain JSONL files by default.
- Run up to `--benchmark-max-concurrency` JD workflows at once, commonly `6`.
- Start the next JD as soon as any active JD finishes.
- Keep process-level judge concurrency at `settings.judge_max_concurrency`, commonly `5`, across the whole benchmark.
- Serialize Weave/W&B uploads in run-completion order.
- Retry failed JD runs and failed uploads once by default.
- Preserve local eval artifacts even when remote upload fails.
- Keep ordinary `seektalent run` behavior unchanged.

## Non-Goals

- Do not add a separate benchmark database or persistent job service.
- Do not add fallback model chains or broad recovery behavior.
- Do not make W&B/Weave upload parallel.
- Do not require humans to maintain a generated combined benchmark JSONL.

## Input Loading

`seektalent benchmark` should support two input modes:

1. Explicit file mode: `--jds-file path/to/file.jsonl` loads only that file, preserving current usage.
2. Default directory mode: when no `--jds-file` is provided, scan `artifacts/benchmarks/*.jsonl`.

Default directory mode skips generated or temporary collections:

- `phase_*.jsonl`
- `*.tmp.jsonl`
- `*.only.jsonl`
- `*.subset.jsonl`

Each loaded row keeps its original fields and gains benchmark metadata:

- `benchmark_file`: the source JSONL path
- `benchmark_group`: existing row value if present, otherwise the source file stem
- `input_index`: stable index after loading all rows

Directory-mode summaries record `benchmark_dir`, `benchmark_files`, `count`, `runs`, and `summary_path`. Explicit file-mode summaries keep the existing `benchmark_file`, `count`, `runs`, and `summary_path` fields.

## Run Scheduling

Benchmark rows enter a single run queue. At most `--benchmark-max-concurrency` rows execute at once. A worker that finishes a row immediately takes the next queued row, so the benchmark does not wait for fixed-size batches to finish.

The final summary keeps rows sorted by `input_index` for stable comparisons. Each row also records completion-order metadata:

- `attempts`
- `status`: `succeeded` or `failed`
- `completion_index` when the run succeeds
- `run_started_at`
- `run_completed_at`
- `error` when the row ultimately fails

If a row fails, it is retried in the same scheduler until the run attempt limit is exhausted. The default is one retry, so each row can run at most two times.

## Eval Scheduling

Eval should split local artifact generation from remote upload.

The local eval stage remains part of each run. It generates:

- `evaluation/evaluation.json`
- `round_01_judge_tasks.jsonl`
- `final_judge_tasks.jsonl`
- `raw_resumes/`
- judge cache writes

All judge calls made during benchmark eval share a benchmark-level limiter. The total number of active judge requests in the process must not exceed `settings.judge_max_concurrency`.

For ordinary `seektalent run`, the existing per-run limiter behavior remains acceptable because there is only one workflow.

## Upload Scheduling

When local eval succeeds and remote eval logging is configured, the completed run enqueues one upload task. Upload tasks are consumed by a single uploader in run-completion order. If eval is disabled or no remote logging project is configured, no upload task is created and the row records `upload_status=skipped`.

The uploader handles Weave and W&B serially. It retries a failed upload once by default. Upload failure does not invalidate the local run or local eval artifacts.

Each summary row records:

- `upload_status`: `skipped`, `succeeded`, or `failed`
- `upload_attempts`
- `upload_error` when upload ultimately fails

W&B report refresh should happen once after all run uploads finish, not once per run. This avoids repeated report rebuilds and reduces W&B global-state interference.

## Error Handling

JD run failure is row-local. The scheduler records the error, retries the row if attempts remain, and continues other rows.

Judge failure is treated as JD run failure because eval belongs to the run's local result. It uses the same row retry path.

Upload failure is not JD run failure. The uploader records upload status and error details while leaving run artifacts intact.

The benchmark writes a summary whenever possible. The process exits with:

- `0` if all JD rows eventually succeed, even if some remote uploads fail.
- `1` if any JD row fails after retries.

This keeps eval correctness separate from remote observability side effects.

## CLI Shape

The existing flags remain:

- `--jds-file`
- `--benchmark-max-concurrency`
- `--enable-eval` / `--disable-eval`

The default for `--jds-file` should become unset. When unset, benchmark uses default directory mode.

Add:

- `--benchmarks-dir`, defaulting to `artifacts/benchmarks`
- `--benchmark-run-retries`, defaulting to `1`
- `--benchmark-upload-retries`, defaulting to `1`

The inspect output and CLI docs should describe directory mode and explicit file mode.

## Testing

Focused tests should cover scheduling behavior without real CTS, LLM, Weave, or W&B calls.

1. Default input scanning loads domain JSONL files and skips generated or temporary files.
2. Loaded rows include `benchmark_file`, `benchmark_group`, and stable `input_index`.
3. Run scheduling respects `--benchmark-max-concurrency` and starts a queued row when any active row completes.
4. Summary rows remain in input order while recording completion order.
5. A failed row retries once and succeeds without blocking unrelated rows.
6. Global judge concurrency stays at `settings.judge_max_concurrency` across multiple concurrent benchmark rows.
7. Upload tasks are serialized in run-completion order.
8. Upload retry failure does not mark the JD run as failed.
9. Benchmark exits `1` when any JD row fails after retries.

## Migration

`artifacts/benchmarks/phase_2_2_pilot.jsonl` can be deleted or left as ignored history. It is no longer the default benchmark input. Users maintain only domain JSONL files.

Existing commands that pass `--jds-file artifacts/benchmarks/phase_2_2_pilot.jsonl` still work as explicit file mode until the file is removed.
