# Outputs

`SeekTalent v0.3 phase 5 runtime loop` returns user-facing results, but still does not persist run artifacts.

`seektalent run` writes the final result to stdout:

- human mode: `stop_reason`, comma-joined shortlist ids, `run_summary`
- `--json` mode: `SearchRunResult.model_dump(mode="json")`

Python API returns the same facts as `SearchRunResult`.

## What currently writes files

### `seektalent init`

Writes one env file, `.env` by default.

### `seektalent doctor`

Ensures the configured `runs` directory exists so path settings stay valid.

That is the only filesystem side effect kept in the CLI besides `init`.

## What exists in memory now

- bootstrap LLM audit snapshots
- search execution runtime audit tags
- scoring payloads and frontier/bootstrap state

These facts are available as structured runtime objects, but are not yet persisted to `runs/<id>/`.

## What is intentionally absent

- `trace.log`
- `events.jsonl`
- `input_truth.json`
- `requirement_sheet.json`
- any round directory
- any controller / reflection / scoring / finalizer artifact
- any UI payload artifact

These outputs stay absent until a later artifact-writing phase lands.

## Related docs

- [CLI](cli.md)
- [Configuration](configuration.md)
- [docs/v-0.3/implementation-checklist.md](v-0.3/implementation-checklist.md)
