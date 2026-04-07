# Architecture

`SeekTalent` is built as a deterministic Python Agent with a small number of LLM-backed stages.

The design goal is controlled behavior and auditability rather than open-ended agent autonomy.

## How To Read The Docs

- This page is the current public-facing overview. It describes the stable system shape, not field-level contracts.
- `docs/v-0.2/` is the current implementation baseline for `HEAD`, including workflow, context, scoring, and CTS enum notes.
- `docs/v-0.3/` is the next-version target design. It defines intended contracts and does not imply that `HEAD` already implements them.
- `docs/v-0.1/` is a historical snapshot kept for older design context only.

## High-level flow

1. Read `JD + notes`
2. Extract structured requirement truth
3. Ask the controller what to search next
4. Build a retrieval plan and execute CTS search
5. Normalize and score candidate resumes
6. Run reflection on the round
7. Repeat until stop
8. Finalize the shortlist

## Main Agent components

### Requirement extractor

- Converts the raw JD and notes into structured requirement data.
- Produces the initial requirement sheet and scoring policy inputs.

### Controller

- Decides whether to continue or stop.
- Proposes round-specific query terms and filter plans.
- Does not directly execute tools.

### Agent runtime

- Owns orchestration, round budgets, pagination, dedup, normalization, scoring fan-out, and stopping rules.
- Persists run artifacts and prompt snapshots.
- Enforces deterministic control flow around LLM stages.

### CTS client

- Executes real CTS requests in authenticated mode.
- Can use a local mock corpus during development and testing.
- Keeps CTS-specific payload construction inside the adapter layer.

### Resume scorer

- Scores normalized resumes in parallel.
- Works on one resume at a time with a shared scoring context.

### Reflection critic

- Reviews the round outcome.
- Provides advice for the next round when reflection is enabled.

### Finalizer

- Produces the final shortlist output and summary artifacts.

## Design boundaries

- One Agent runtime controls the process.
- Tool execution is explicit and limited.
- Audit files are first-class outputs.
- The repository includes a minimal web UI, but the CLI remains the primary interface.
