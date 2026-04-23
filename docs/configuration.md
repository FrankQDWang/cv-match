# Configuration

`SeekTalent` reads runtime settings from environment variables.

- `SEEKTALENT_*` variables are loaded by `pydantic-settings`.
- Provider variables such as `OPENAI_API_KEY` and `OPENAI_BASE_URL` are also read from `.env` at process start.
- `seektalent init` writes the starter env template from `.env.example` in a source checkout, or from `src/seektalent/default.env` in an installed package.

In this repository, `.env.example` is the editable source of the starter env. `src/seektalent/default.env` is its packaged mirror.

## Minimal Setup

For a real CTS run, you need:

```dotenv
OPENAI_API_KEY=your-openai-compatible-key
SEEKTALENT_CTS_TENANT_KEY=your-cts-tenant-key
SEEKTALENT_CTS_TENANT_SECRET=your-cts-tenant-secret
```

The current starter env routes OpenAI-family calls through DashScope-compatible mode:

```dotenv
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

If you use an official OpenAI endpoint, leave `OPENAI_BASE_URL` empty and configure model ids accordingly.

## Starter Env Values

The generated starter env currently uses these main values:

```dotenv
OPENAI_API_KEY=
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

SEEKTALENT_CTS_BASE_URL=https://link.hewa.cn
SEEKTALENT_CTS_TENANT_KEY=
SEEKTALENT_CTS_TENANT_SECRET=
SEEKTALENT_CTS_TIMEOUT_SECONDS=20
SEEKTALENT_CTS_SPEC_PATH=cts.validated.yaml

SEEKTALENT_REQUIREMENTS_MODEL=openai-chat:deepseek-v3.2
SEEKTALENT_CONTROLLER_MODEL=openai-chat:deepseek-v3.2
SEEKTALENT_SCORING_MODEL=openai-chat:deepseek-v3.2
SEEKTALENT_FINALIZE_MODEL=openai-chat:deepseek-v3.2
SEEKTALENT_REFLECTION_MODEL=openai-chat:deepseek-v3.2
SEEKTALENT_JUDGE_MODEL=openai-responses:gpt-5.4
SEEKTALENT_JUDGE_OPENAI_BASE_URL=http://127.0.0.1:8317/v1/responses
SEEKTALENT_JUDGE_OPENAI_API_KEY=
SEEKTALENT_REASONING_EFFORT=off
SEEKTALENT_JUDGE_REASONING_EFFORT=high
SEEKTALENT_CONTROLLER_ENABLE_THINKING=true
SEEKTALENT_REFLECTION_ENABLE_THINKING=true

SEEKTALENT_MIN_ROUNDS=3
SEEKTALENT_MAX_ROUNDS=10
SEEKTALENT_SCORING_MAX_CONCURRENCY=5
SEEKTALENT_JUDGE_MAX_CONCURRENCY=5
SEEKTALENT_SEARCH_MAX_PAGES_PER_ROUND=3
SEEKTALENT_SEARCH_MAX_ATTEMPTS_PER_ROUND=3
SEEKTALENT_SEARCH_NO_PROGRESS_LIMIT=2
SEEKTALENT_MOCK_CTS=false
SEEKTALENT_ENABLE_EVAL=false
SEEKTALENT_ENABLE_REFLECTION=true
SEEKTALENT_CANDIDATE_FEEDBACK_ENABLED=true
SEEKTALENT_TARGET_COMPANY_ENABLED=false
SEEKTALENT_COMPANY_DISCOVERY_ENABLED=true
SEEKTALENT_COMPANY_DISCOVERY_PROVIDER=bocha
SEEKTALENT_BOCHA_API_KEY=
SEEKTALENT_RUNS_DIR=runs
```

The code-level fallback defaults in `AppSettings` are intentionally still valid without the starter env. For example, model fallbacks use OpenAI Responses model ids, while the starter env overrides them for the current local DashScope setup.

## Provider Variables

| Variable | Required | Notes |
| --- | --- | --- |
| `OPENAI_API_KEY` | Required for `openai:*`, `openai-chat:*`, and `openai-responses:*` model ids | Used for official OpenAI and OpenAI-compatible endpoints. |
| `OPENAI_BASE_URL` | Optional | Set this for OpenAI-compatible endpoints such as DashScope. Leave empty for the official OpenAI endpoint. |
| `ANTHROPIC_API_KEY` | Required only for `anthropic:*` model ids | Requires installing the matching Pydantic AI extra. |
| `GOOGLE_API_KEY` | Required only for `google-gla:*` model ids | Requires installing the matching Pydantic AI extra. |

## CTS Variables

| Variable | Required | Starter value | Notes |
| --- | --- | --- | --- |
| `SEEKTALENT_CTS_BASE_URL` | No | `https://link.hewa.cn` | Base URL for CTS. |
| `SEEKTALENT_CTS_TENANT_KEY` | Required in real CTS mode | empty | Sent as the `tenant_key` header. |
| `SEEKTALENT_CTS_TENANT_SECRET` | Required in real CTS mode | empty | Sent as the `tenant_secret` header. |
| `SEEKTALENT_CTS_TIMEOUT_SECONDS` | No | `20` | HTTP timeout for CTS requests. |
| `SEEKTALENT_CTS_SPEC_PATH` | No | `cts.validated.yaml` | Default resolves to the packaged CTS spec. Custom values resolve relative to the current working directory unless absolute. |

## Model Variables

All model settings must use `provider:model`.

| Variable | Starter value | Notes |
| --- | --- | --- |
| `SEEKTALENT_REQUIREMENTS_MODEL` | `openai-chat:deepseek-v3.2` | Requirement extraction. |
| `SEEKTALENT_CONTROLLER_MODEL` | `openai-chat:deepseek-v3.2` | Round controller. |
| `SEEKTALENT_SCORING_MODEL` | `openai-chat:deepseek-v3.2` | Per-resume scoring. |
| `SEEKTALENT_FINALIZE_MODEL` | `openai-chat:deepseek-v3.2` | Final shortlist presentation. |
| `SEEKTALENT_REFLECTION_MODEL` | `openai-chat:deepseek-v3.2` | Round reflection. |
| `SEEKTALENT_JUDGE_MODEL` | `openai-responses:gpt-5.4` | Optional eval judge. Falls back to the scoring model if unset. |
| `SEEKTALENT_JUDGE_OPENAI_BASE_URL` | `http://127.0.0.1:8317/v1/responses` | Optional endpoint override for judge calls. |
| `SEEKTALENT_JUDGE_OPENAI_API_KEY` | empty | Optional API key override for judge calls. |
| `SEEKTALENT_TUI_SUMMARY_MODEL` | unset | Optional model for short progress summaries. Falls back to the scoring model. |

Reasoning effort values are `off`, `low`, `medium`, and `high`.

| Variable | Starter value | Notes |
| --- | --- | --- |
| `SEEKTALENT_REASONING_EFFORT` | `off` | Default effort for model calls unless a stage-specific value overrides it. |
| `SEEKTALENT_JUDGE_REASONING_EFFORT` | `high` | Judge effort. Falls back to `SEEKTALENT_REASONING_EFFORT` if unset. |
| `SEEKTALENT_CONTROLLER_ENABLE_THINKING` | `true` | Passed as Bailian `enable_thinking` for supported controller models. |
| `SEEKTALENT_REFLECTION_ENABLE_THINKING` | `true` | Passed as Bailian `enable_thinking` for supported reflection models. |

`openai-responses:*` model calls also set low text verbosity. When reasoning is enabled, they request concise reasoning summaries.

## Runtime Variables

| Variable | Starter value | Notes |
| --- | --- | --- |
| `SEEKTALENT_MIN_ROUNDS` | `3` | Minimum completed retrieval rounds before stopping is allowed. |
| `SEEKTALENT_MAX_ROUNDS` | `10` | Hard cap for controller/search rounds. Must be `>= min_rounds` and `<= 10`. |
| `SEEKTALENT_SCORING_MAX_CONCURRENCY` | `5` | Max concurrent per-resume scoring calls. |
| `SEEKTALENT_SEARCH_MAX_PAGES_PER_ROUND` | `3` | Per-round CTS page budget. |
| `SEEKTALENT_SEARCH_MAX_ATTEMPTS_PER_ROUND` | `3` | Per-round CTS attempt budget. |
| `SEEKTALENT_SEARCH_NO_PROGRESS_LIMIT` | `2` | Repeated no-progress threshold. |
| `SEEKTALENT_ENABLE_REFLECTION` | `true` | Enables reflection after each completed round. |
| `SEEKTALENT_RUNS_DIR` | `runs` | Output root. Relative paths resolve from the current working directory. |

## Eval Variables

Eval is off by default. Enable it with `SEEKTALENT_ENABLE_EVAL=true` or the CLI `--enable-eval` flag.

| Variable | Starter value | Notes |
| --- | --- | --- |
| `SEEKTALENT_ENABLE_EVAL` | `false` | Enables judge + evaluation artifacts. |
| `SEEKTALENT_JUDGE_MAX_CONCURRENCY` | `5` | Max concurrent judge calls. |
| `SEEKTALENT_WANDB_ENTITY` | local template value | Optional W&B entity for eval/report logging. |
| `SEEKTALENT_WANDB_PROJECT` | `seektalent` | Optional W&B project. |
| `SEEKTALENT_WEAVE_ENTITY` | local template value | Optional Weave entity. Falls back to W&B entity when unset. |
| `SEEKTALENT_WEAVE_PROJECT` | `seektalent` | Optional Weave project. |

## Rescue And Discovery Variables

These settings control low-quality recall repair lanes.

| Variable | Starter value | Notes |
| --- | --- | --- |
| `SEEKTALENT_CANDIDATE_FEEDBACK_ENABLED` | `true` | Allows runtime to derive a safe expansion term from strong scored candidates. |
| `SEEKTALENT_CANDIDATE_FEEDBACK_MODEL` | `openai-chat:qwen3.5-flash` | Reserved for model-ranked candidate feedback steps. |
| `SEEKTALENT_CANDIDATE_FEEDBACK_REASONING_EFFORT` | `off` | Reasoning effort for candidate feedback model steps. |
| `SEEKTALENT_TARGET_COMPANY_ENABLED` | `false` | Explicit target-company bootstrap is disabled by default. |
| `SEEKTALENT_COMPANY_DISCOVERY_ENABLED` | `true` | Allows bounded web company discovery when quality gates require rescue. |
| `SEEKTALENT_COMPANY_DISCOVERY_PROVIDER` | `bocha` | Only `bocha` is supported. |
| `SEEKTALENT_BOCHA_API_KEY` | empty | Required only when web company discovery actually runs. |
| `SEEKTALENT_COMPANY_DISCOVERY_MODEL` | `openai-chat:qwen3.5-flash` | Model for search planning, evidence extraction, and plan reduction. |
| `SEEKTALENT_COMPANY_DISCOVERY_REASONING_EFFORT` | `off` | Reasoning effort for company discovery model steps. |
| `SEEKTALENT_COMPANY_DISCOVERY_MAX_SEARCH_CALLS` | `4` | Max Bocha search calls in one discovery workflow. |
| `SEEKTALENT_COMPANY_DISCOVERY_MAX_RESULTS_PER_QUERY` | `30` | Max search results per query. |
| `SEEKTALENT_COMPANY_DISCOVERY_MAX_OPEN_PAGES` | `8` | Max pages opened after rerank. |
| `SEEKTALENT_COMPANY_DISCOVERY_TIMEOUT_SECONDS` | `25` | Wall-clock budget for discovery. |
| `SEEKTALENT_COMPANY_DISCOVERY_ACCEPTED_COMPANY_LIMIT` | `8` | Max accepted companies injected into the term pool. |
| `SEEKTALENT_COMPANY_DISCOVERY_MIN_CONFIDENCE` | `0.65` | Minimum accepted company confidence. |

## Development-Only Mock CTS

| Variable | Starter value | Notes |
| --- | --- | --- |
| `SEEKTALENT_MOCK_CTS` | `false` | Enables the local mock CTS corpus in source-checkout development. The published CLI rejects this mode. |

## Provider Matching Rules

Before each run, the runtime checks credentials for configured model prefixes:

- OpenAI-family models require `OPENAI_API_KEY`.
- Anthropic models require `ANTHROPIC_API_KEY`.
- Google GLA models require `GOOGLE_API_KEY`.
- Real CTS mode requires both CTS tenant credentials.

Use `seektalent doctor` to validate local configuration without making network calls.

## Related Docs

- [CLI](cli.md)
- [UI](ui.md)
- [Outputs](outputs.md)
