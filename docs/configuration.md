# Configuration

`deepmatch` reads configuration from environment variables. By default:

- `DEEPMATCH_*` settings are loaded through `pydantic-settings`
- selected provider variables are loaded from `.env` at process start

The recommended way to create a starter env file is:

```bash
deepmatch init
```

You can also write to a custom path:

```bash
deepmatch init --env-file ./local.env
```

## Minimal setup

For a normal local setup, you usually need:

- one working LLM provider key
- CTS credentials
- the default model IDs are usually enough

Minimum values for a real CTS run:

```dotenv
OPENAI_API_KEY=your-openai-key
DEEPMATCH_CTS_TENANT_KEY=your-cts-tenant-key
DEEPMATCH_CTS_TENANT_SECRET=your-cts-tenant-secret
```

If you keep the default `openai-responses:*` models, `OPENAI_API_KEY` is the only provider key you need.

## Example `.env`

```dotenv
OPENAI_API_KEY=
OPENAI_BASE_URL=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

DEEPMATCH_CTS_BASE_URL=https://link.hewa.cn
DEEPMATCH_CTS_TENANT_KEY=
DEEPMATCH_CTS_TENANT_SECRET=
DEEPMATCH_CTS_TIMEOUT_SECONDS=20
DEEPMATCH_CTS_SPEC_PATH=cts.validated.yaml

DEEPMATCH_REQUIREMENTS_MODEL=openai-responses:gpt-5.4-mini
DEEPMATCH_CONTROLLER_MODEL=openai-responses:gpt-5.4-mini
DEEPMATCH_SCORING_MODEL=openai-responses:gpt-5.4-mini
DEEPMATCH_FINALIZE_MODEL=openai-responses:gpt-5.4-mini
DEEPMATCH_REFLECTION_MODEL=openai-responses:gpt-5.4
DEEPMATCH_REASONING_EFFORT=medium

DEEPMATCH_MIN_ROUNDS=3
DEEPMATCH_MAX_ROUNDS=5
DEEPMATCH_SCORING_MAX_CONCURRENCY=5
DEEPMATCH_SEARCH_MAX_PAGES_PER_ROUND=3
DEEPMATCH_SEARCH_MAX_ATTEMPTS_PER_ROUND=3
DEEPMATCH_SEARCH_NO_PROGRESS_LIMIT=2
DEEPMATCH_MOCK_CTS=false
DEEPMATCH_ENABLE_REFLECTION=true
DEEPMATCH_RUNS_DIR=runs
```

## LLM provider variables

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | Required for `openai:*`, `openai-chat:*`, `openai-responses:*` models | empty | Needed if any configured model uses an OpenAI-family provider prefix. |
| `OPENAI_BASE_URL` | Optional | unset | Use this when routing OpenAI-compatible traffic to a custom endpoint. |
| `ANTHROPIC_API_KEY` | Required for `anthropic:*` models | empty | Needed if any configured model uses the Anthropic provider. |
| `GOOGLE_API_KEY` | Required for `google-gla:*` models | empty | Needed if any configured model uses the Google provider. |

## CTS variables

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `DEEPMATCH_CTS_BASE_URL` | No | `https://link.hewa.cn` | Base URL for the CTS service. |
| `DEEPMATCH_CTS_TENANT_KEY` | Required in real CTS mode | `None` | Used as the `tenant_key` request header. |
| `DEEPMATCH_CTS_TENANT_SECRET` | Required in real CTS mode | `None` | Used as the `tenant_secret` request header. |
| `DEEPMATCH_CTS_TIMEOUT_SECONDS` | No | `20` | HTTP timeout for CTS requests. |
| `DEEPMATCH_CTS_SPEC_PATH` | No | `cts.validated.yaml` | If left as the default, `deepmatch` uses the packaged spec file. If you set a different value, it is resolved relative to the current working directory unless absolute. |

## Model variables

All model settings must use the `provider:model` format.

| Variable | Required | Default |
| --- | --- | --- |
| `DEEPMATCH_REQUIREMENTS_MODEL` | No | `openai-responses:gpt-5.4-mini` |
| `DEEPMATCH_CONTROLLER_MODEL` | No | `openai-responses:gpt-5.4-mini` |
| `DEEPMATCH_SCORING_MODEL` | No | `openai-responses:gpt-5.4-mini` |
| `DEEPMATCH_FINALIZE_MODEL` | No | `openai-responses:gpt-5.4-mini` |
| `DEEPMATCH_REFLECTION_MODEL` | No | `openai-responses:gpt-5.4` |
| `DEEPMATCH_REASONING_EFFORT` | No | `medium` |

Notes:

- valid reasoning effort values are `low`, `medium`, and `high`
- `openai-responses:*` models additionally use `reasoning_summary=concise` and `text_verbosity=low`

## Agent variables

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `DEEPMATCH_MIN_ROUNDS` | No | `3` | Minimum number of rounds before stopping is allowed. |
| `DEEPMATCH_MAX_ROUNDS` | No | `5` | Hard stop for the Agent. Must be `>= min_rounds`. |
| `DEEPMATCH_SCORING_MAX_CONCURRENCY` | No | `5` | Max parallel per-resume scoring workers. |
| `DEEPMATCH_SEARCH_MAX_PAGES_PER_ROUND` | No | `3` | Per-round pagination budget. |
| `DEEPMATCH_SEARCH_MAX_ATTEMPTS_PER_ROUND` | No | `3` | Per-round CTS fetch attempt limit. |
| `DEEPMATCH_SEARCH_NO_PROGRESS_LIMIT` | No | `2` | Repeated no-progress threshold. |
| `DEEPMATCH_ENABLE_REFLECTION` | No | `true` | Enables the reflection step at the end of each round. |
| `DEEPMATCH_RUNS_DIR` | No | `runs` | Root output directory for run artifacts. Resolved relative to the current working directory unless absolute. |

## Provider matching rules

Before each run, the runtime checks provider credentials based on the configured model prefixes:

- OpenAI-family models require `OPENAI_API_KEY`
- Anthropic models require `ANTHROPIC_API_KEY`
- Google GLA models require `GOOGLE_API_KEY`

Use `deepmatch doctor` to validate the current local setup without making network calls:

```bash
deepmatch doctor
```

## Development-only setting

| Variable | Default | Notes |
| --- | --- | --- |
| `DEEPMATCH_MOCK_CTS` | `false` | Enables the local mock CTS client. Use this for local development and tests. |

## Related docs

- [CLI](cli.md)
- [UI](ui.md)
- [Outputs](outputs.md)
