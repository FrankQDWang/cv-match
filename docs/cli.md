# CLI

[简体中文](cli.zh-CN.md)

The canonical CLI entrypoint is:

```bash
seektalent --help
```

Recommended black-box sequence:

```bash
seektalent --help
seektalent doctor
seektalent run --jd-file ./jd.md
seektalent update
```

## Commands

### `seektalent init`

Write a starter env file in the current directory:

```bash
seektalent init
```

Write to a custom path:

```bash
seektalent init --env-file ./local.env
```

Overwrite an existing file:

```bash
seektalent init --force
```

### `seektalent doctor`

Run local checks without network calls:

```bash
seektalent doctor
```

Machine-readable output:

```bash
seektalent doctor --json
```

### `seektalent version`

Print the installed package version:

```bash
seektalent version
```

### `seektalent update`

Print upgrade instructions for pip and pipx installs:

```bash
seektalent update
```

## `seektalent run`

Each run requires one required input and one optional supplement:

- a job description
- optional sourcing notes / sourcing preferences

You must provide the job description with exactly one source:

- `--jd` or `--jd-file`

If you want to add sourcing preferences, provide them with exactly one source:

- `--notes` or `--notes-file`

### Run with only a JD

```bash
seektalent run \
  --jd "Python agent engineer with retrieval and ranking experience"
```

### Run from inline text

```bash
seektalent run \
  --jd "Python agent engineer with retrieval and ranking experience" \
  --notes "Shanghai preferred, avoid pure frontend profiles"
```

### Run from files

```bash
seektalent run \
  --jd-file ./jd.md \
  --notes-file ./notes.md
```

### Override output location

```bash
seektalent run \
  --jd "Python agent engineer" \
  --notes "Shanghai preferred" \
  --output-dir ./outputs
```

### Use a custom env file

```bash
seektalent run \
  --jd "Python agent engineer" \
  --notes "Shanghai preferred" \
  --env-file ./local.env
```

### Machine-readable output

```bash
seektalent run \
  --jd "Python agent engineer" \
  --notes "Shanghai preferred" \
  --json
```

In `--json` mode, stdout contains exactly one JSON object on success. On failure, stderr contains exactly one JSON object.

## Success output

Default success output is human-readable:

- final markdown answer
- `run_id`
- `run_directory`
- `trace_log`

When `--output-dir` is omitted, artifacts go under `./runs` relative to the current working directory.

## Failure behavior

The CLI fails fast when:

- the job description is missing
- both inline and file input are supplied for the same field
- model configuration is invalid
- provider credentials are missing
- CTS credentials are missing
- mock CTS is requested through configuration
- any runtime stage raises an exception

## Related docs

- [Configuration](configuration.md)
- [Outputs](outputs.md)
