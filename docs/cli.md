# CLI

The CLI entrypoint is:

```bash
uv run cv-match --help
```

Current options:

```text
--jd
--notes
--jd-file
--notes-file
--mock-cts
--real-cts
--max-rounds
--min-rounds
--scoring-max-concurrency
--search-max-pages-per-round
--search-max-attempts-per-round
--search-no-progress-limit
--enable-reflection
--disable-reflection
```

## Required input

Each run requires two pieces of input:

- a job description
- sourcing notes / sourcing preferences

You can provide each value either inline or through a file.

## Common commands

### Run from files in mock CTS mode

```bash
uv run cv-match --jd-file examples/jd.md --notes-file examples/notes.md --mock-cts
```

### Run from inline text

```bash
uv run cv-match \
  --jd "Python agent engineer with retrieval and ranking experience" \
  --notes "Shanghai preferred, avoid pure frontend profiles" \
  --mock-cts
```

### Run against real CTS

```bash
uv run cv-match --jd-file examples/jd.md --notes-file examples/notes.md --real-cts
```

### Override Agent limits for one run

```bash
uv run cv-match \
  --jd-file examples/jd.md \
  --notes-file examples/notes.md \
  --mock-cts \
  --min-rounds 2 \
  --max-rounds 4 \
  --scoring-max-concurrency 3
```

## Output

On success, the CLI prints:

- the final markdown answer
- `run_id`
- `run_directory`
- `trace_log`

Example:

```text
run_id: abc12345
run_directory: runs/20260402_120000_abc12345
trace_log: runs/20260402_120000_abc12345/trace.log
```

## Failure behavior

The CLI fails fast and prints a single error line to stderr when:

- required input is missing
- model configuration is invalid
- provider credentials are missing
- real CTS credentials are missing in `--real-cts` mode
- any Agent stage raises an exception

## Notes

- Mock CTS avoids live CTS traffic, but it does not avoid live LLM calls.
- Agent configuration can come from `.env`, and CLI flags override selected Agent settings for the current run.

## Related docs

- [Configuration](configuration.md)
- [Outputs](outputs.md)
