# Pi OpenCLI Browser Backend For Liepin Card Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Pi-internal OpenCLI read/action backend for Liepin card-search spike, with OpenCLI CLI installed as a project dependency and the OpenCLI Chrome extension installed manually by the user.

**Architecture:** Runtime and Workbench keep the existing source-lane boundary. Pi receives bounded Liepin card-search tasks, uses a repo-owned OpenCLI extension that shells only through a Python restricted helper, reads/actions through one named OpenCLI browser session, and returns the existing strict Liepin card envelope. OpenCLI is not exposed to Runtime, Workbench, or the model as a raw CLI.

**Tech Stack:** Python 3.12, pytest, Pydantic settings, Pi RPC, Pi TypeScript extensions, TypeBox, Node `child_process`, local `@jackwener/opencli` dependency, Svelte safe reason mapping.

---

Linked spec: [2026-05-20-pi-macos-action-backend-liepin-card-search-design.md](../specs/2026-05-20-pi-macos-action-backend-liepin-card-search-design.md)

## File Structure

- Modify `apps/web-svelte/package.json`
  - Add `@jackwener/opencli` as a dependency so the CLI is installed with project dependencies.
  - Add direct `typebox` dependency because the Pi extension imports TypeBox schemas.
- Modify `apps/web-svelte/bun.lock`
  - Lock the OpenCLI dependency through `bun install`.
- Modify `src/seektalent/config.py`
  - Add OpenCLI backend settings and safe validation.
  - Resolve the default OpenCLI binary from `apps/web-svelte/node_modules/.bin/opencli`.
  - Include the repo-owned OpenCLI Pi extension in `liepin_pi_command_argv` when backend is `opencli`.
- Modify `src/seektalent/runtime/source_lanes.py`
  - Allowlist `liepin_opencli_*` safe reason codes in Runtime public serializers.
- Modify `src/seektalent/providers/liepin/runtime_lane.py`
  - Preserve OpenCLI safe reason codes when mapping Pi worker failures into Runtime lane results.
- Modify `src/seektalent/providers/pi_agent/pi_external.py`
  - Make the Pi prompt browser-backend-aware so OpenCLI mode is not instructed to use DokoBot.
- Modify `src/seektalent/default.env`, `.env.example`
  - Document the OpenCLI backend defaults and that the browser extension is user-installed.
- Create `src/seektalent/providers/pi_agent/opencli_browser.py`
  - Restricted Python wrapper for OpenCLI browser commands.
  - Defines Liepin source policy, explicit action methods, budgets, host/start URL checks, deterministic state classifier, tab lease/reuse helpers, Pi-only observation projection, public-safe result projection, and command execution through injectable runners.
- Create `src/seektalent/providers/pi_agent/opencli_browser_cli.py`
  - JSON stdin/stdout command entrypoint called by the Pi extension.
  - Accepts only a SeekTalent action name in argv; payload comes from stdin.
- Create `src/seektalent/providers/pi_agent/pi_extensions/seektalent_opencli_browser.ts`
  - Registers `seektalent_opencli_*` Pi tools.
  - Calls the Python helper, drains stdout/stderr with bounded buffers, returns bounded observations only to Pi tool calls, enforces task budgets, and denies raw OpenCLI access.
- Modify `src/seektalent/providers/pi_agent/local_setup.py`
  - Add static OpenCLI readiness components.
  - In OpenCLI mode, skip DokoBot/MCP adapter requirements so Liepin readiness is controlled by the OpenCLI browser component only.
- Modify `src/seektalent/dev_mode.py`
  - Surface OpenCLI readiness in developer diagnostics only.
- Modify `src/seektalent/providers/liepin/pi_executor.py`
  - Accept OpenCLI capability readiness as an alternative to DokoBot readiness for OpenCLI mode.
  - Add optional envelope `safe_reason_code` support for OpenCLI backend-specific stop reasons.
  - Preserve existing strict Liepin card envelope validation.
- Modify `src/seektalent/providers/liepin/pi_worker_client.py`, `src/seektalent/providers/liepin/client.py`
  - Pass OpenCLI backend expectations into the executor/client boundary.
- Modify `src/seektalent/providers/pi_agent/pi_skills/liepin_search_cards.md`
  - Describe the OpenCLI read/action loop, tab-only behavior, and stop states.
- Modify `src/seektalent_ui/workbench_routes.py`
  - Preserve new `liepin_opencli_*` reason codes in source-state projection.
- Modify `apps/web-svelte/src/lib/workbench/sourceDisplay.ts`
  - Map OpenCLI setup/runtime reasons to category-specific browser-channel business copy.
- Modify `tests/test_liepin_config.py`
  - Settings and command-shape coverage.
- Create `tests/test_pi_opencli_browser.py`
  - Unit tests for wrapper policy, allowed/forbidden commands, CLI output, and no path/secret leaks.
- Modify `tests/test_liepin_pi_executor.py`, `tests/test_liepin_pi_worker_client.py`
  - Capability probe and worker error mapping coverage.
- Modify `tests/test_liepin_runtime_source_lane.py`, `tests/test_runtime_source_lanes.py`
  - Runtime reason mapping and public serializer coverage for OpenCLI safe reason codes.
- Modify `tests/test_pi_external_agent.py`
  - OpenCLI extension and backend-aware prompt coverage.
- Modify `tests/test_dev_mode_readiness.py`
  - Static OpenCLI readiness diagnostics.
- Modify `tests/test_pi_agent_boundaries.py`
  - Ensure Runtime/Workbench do not call OpenCLI directly and forbidden OpenCLI commands remain inaccessible.
- Modify `README.md`, `docs/configuration.md`, `docs/development.md`
  - Document OpenCLI CLI dependency, user-installed Chrome extension, safe limitations, and manual spike checks.
  - Document that source/dev workspaces auto-install OpenCLI through the Svelte dependency path, while packaged/PyPI distribution must either bundle/bootstrap the Node dependency tree or fail closed.

## Task 0: OpenCLI Runtime Reason And Envelope Plumbing

**Files:**
- Modify: `src/seektalent/runtime/source_lanes.py`
- Modify: `src/seektalent/providers/liepin/runtime_lane.py`
- Modify: `src/seektalent/providers/liepin/pi_executor.py`
- Modify: `src/seektalent/providers/pi_agent/pi_external.py`
- Test: `tests/test_runtime_source_lanes.py`
- Test: `tests/test_liepin_runtime_source_lane.py`
- Test: `tests/test_liepin_pi_executor.py`
- Test: `tests/test_pi_external_agent.py`

- [ ] **Step 1: Add Runtime public serializer test**

Add to `tests/test_runtime_source_lanes.py`:

```python
def test_opencli_safe_reason_code_survives_runtime_public_payload() -> None:
    event = RuntimeSourceLaneEvent(
        schema_version="runtime_source_lane_event_v1",
        runtime_run_id="run-1",
        source_plan_id="plan-1",
        source_lane_run_id="lane-1",
        source="liepin",
        attempt=1,
        event_seq=1,
        event_type="source_lane_blocked",
        status="blocked",
        safe_reason_code="liepin_opencli_extension_disconnected",
    )

    payload = event.to_public_payload()

    assert payload["safe_reason_code"] == "liepin_opencli_extension_disconnected"
```

- [ ] **Step 2: Add Runtime lane mapping test**

Add to `tests/test_liepin_runtime_source_lane.py`:

```python
def test_pi_failure_codes_preserve_opencli_safe_reason_codes() -> None:
    assert runtime_safe_reason_code_from_pi_failure_code("liepin_opencli_extension_disconnected") == (
        "liepin_opencli_extension_disconnected"
    )
    assert runtime_safe_reason_code_from_pi_failure_code("liepin_opencli_login_required") == (
        "liepin_opencli_login_required"
    )
    assert runtime_safe_reason_code_from_pi_failure_code("liepin_opencli_risk_page") == "liepin_opencli_risk_page"
```

- [ ] **Step 3: Add Pi envelope safe reason test**

Add to `tests/test_liepin_pi_executor.py`:

```python
def test_card_envelope_preserves_opencli_safe_reason_code() -> None:
    final_text = """
{"schema_version":"seektalent.pi_liepin_cards.v1","status":"blocked","stop_reason":"blocked_backend_unavailable","safe_reason_code":"liepin_opencli_identity_intercept","source_run_id":"run-1","query":"python ranking","cards_seen":0,"cards_returned":0,"pages_visited":1,"action_trace_ref":"artifact://protected/pi-trace/run-1","safe_summary_refs":[],"protected_snapshot_refs":[],"cards":[]}
""".strip()
    executor = PiLiepinExecutor(
        client=_client(final_text),
        key_hasher=FakeProviderKeyHasher(),
        artifact_registry=_registry("artifact://protected/pi-trace/run-1"),
    )

    result = executor.search_cards(
        source_run_id="run-1",
        keyword_query="python ranking",
        query_terms=("python", "ranking"),
        page_size=10,
        max_pages=1,
        max_cards=10,
    )

    assert result.safe_reason_code == "liepin_opencli_identity_intercept"
```

- [ ] **Step 4: Add backend-aware prompt test**

Add to `tests/test_pi_external_agent.py`:

```python
def test_pi_prompt_can_describe_opencli_backend_without_dokobot_wording(tmp_path: Path) -> None:
    skill = tmp_path / "skill.md"
    skill.write_text("skill", encoding="utf-8")
    client = PiRpcAgentClient(
        command=("pi", "--mode", "rpc", "--no-session", "--no-skills", "--skill", str(skill)),
        skill_path=skill,
        dokobot_tool_name="dokobot",
        timeout_seconds=5,
        artifact_root=tmp_path / "artifacts",
        transport=FakeRpcTransport(PiRpcTaskResult(status=PiRpcTaskStatus.SUCCEEDED, final_text="{}")),
        browser_backend_description="SeekTalent OpenCLI browser tools: seektalent_opencli_status",
    )

    prompt = client._build_prompt("{}")

    assert "SeekTalent OpenCLI browser tools" in prompt
    assert "Required DokoBot tool inside Pi" not in prompt
```

- [ ] **Step 5: Run focused tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_runtime_source_lanes.py::test_opencli_safe_reason_code_survives_runtime_public_payload tests/test_liepin_runtime_source_lane.py::test_pi_failure_codes_preserve_opencli_safe_reason_codes tests/test_liepin_pi_executor.py::test_card_envelope_preserves_opencli_safe_reason_code tests/test_pi_external_agent.py::test_pi_prompt_can_describe_opencli_backend_without_dokobot_wording -q
```

Expected: fail because OpenCLI reason codes, envelope `safe_reason_code`, and backend-aware prompt support do not exist.

- [ ] **Step 6: Add shared OpenCLI safe reason set**

In `src/seektalent/providers/liepin/runtime_lane.py`, add near `runtime_safe_reason_code_from_pi_failure_code`:

```python
OPENCLI_SAFE_REASON_CODES = frozenset(
    {
        "liepin_opencli_backend_disabled",
        "liepin_opencli_command_missing",
        "liepin_opencli_extension_disconnected",
        "liepin_opencli_status_unavailable",
        "liepin_opencli_forbidden_command",
        "liepin_opencli_forbidden_text",
        "liepin_opencli_host_blocked",
        "liepin_opencli_start_url_blocked",
        "liepin_opencli_window_policy_blocked",
        "liepin_opencli_budget_exhausted",
        "liepin_opencli_timeout",
        "liepin_opencli_login_required",
        "liepin_opencli_identity_intercept",
        "liepin_opencli_risk_page",
        "liepin_opencli_unknown_modal",
        "liepin_opencli_source_policy_missing",
        "liepin_opencli_malformed_state",
    }
)
```

Then add at the top of `runtime_safe_reason_code_from_pi_failure_code` after `value = ...`:

```python
    if value in OPENCLI_SAFE_REASON_CODES:
        return value
```

- [ ] **Step 7: Allowlist OpenCLI reasons in Runtime public payloads**

In `src/seektalent/runtime/source_lanes.py`, add the same `liepin_opencli_*` values to `_SAFE_REASON_CODES`. Keep them as literal strings in this module to avoid creating a runtime-to-provider import dependency.

- [ ] **Step 8: Add optional Pi card envelope safe reason**

In `src/seektalent/providers/liepin/pi_executor.py`, add:

```python
OPENCLI_SAFE_REASON_CODES = frozenset(
    {
        "liepin_opencli_backend_disabled",
        "liepin_opencli_command_missing",
        "liepin_opencli_extension_disconnected",
        "liepin_opencli_status_unavailable",
        "liepin_opencli_forbidden_command",
        "liepin_opencli_forbidden_text",
        "liepin_opencli_host_blocked",
        "liepin_opencli_start_url_blocked",
        "liepin_opencli_window_policy_blocked",
        "liepin_opencli_budget_exhausted",
        "liepin_opencli_timeout",
        "liepin_opencli_login_required",
        "liepin_opencli_identity_intercept",
        "liepin_opencli_risk_page",
        "liepin_opencli_unknown_modal",
        "liepin_opencli_source_policy_missing",
        "liepin_opencli_malformed_state",
    }
)
```

Add to `_PiLiepinCardsEnvelope`:

```python
    safe_reason_code: str | None = None
```

In `_PiLiepinCardsEnvelope.validate_counts`, after the `stop_reason` checks:

```python
        if self.safe_reason_code is not None and self.safe_reason_code not in OPENCLI_SAFE_REASON_CODES:
            raise ValueError("safe_reason_code must be an allowlisted OpenCLI reason")
```

In `PiLiepinExecutor.search_cards`, replace:

```python
        safe_reason = _safe_reason_for_stop(stop_reason)
```

with:

```python
        safe_reason = envelope.safe_reason_code or _safe_reason_for_stop(stop_reason)
```

Do not allow `liepin_opencli_*` values in `stop_reason`.

- [ ] **Step 9: Make Pi prompt backend-aware**

In `src/seektalent/providers/pi_agent/pi_external.py`, add `browser_backend_description: str | None = None` to `PiRpcAgentClient.__init__`, store it as `self._browser_backend_description`, and change `_build_prompt` to:

```python
    def _build_prompt(self, prompt: str) -> str:
        backend_line = (
            f"Required browser backend inside Pi: {self._browser_backend_description}\n"
            if self._browser_backend_description
            else f"Required DokoBot tool inside Pi: {self._dokobot_tool_name}\n"
        )
        return (
            f"Required loaded skill path: {self._skill_path}\n"
            f"{backend_line}"
            f"Required artifact root: {self._artifact_root}\n"
            "Write every artifact://protected/... and artifact://public-summary/... ref to that root before returning final JSON.\n"
            f"{prompt}"
        )
```

- [ ] **Step 10: Re-run focused tests**

Run:

```bash
uv run pytest tests/test_runtime_source_lanes.py::test_opencli_safe_reason_code_survives_runtime_public_payload tests/test_liepin_runtime_source_lane.py::test_pi_failure_codes_preserve_opencli_safe_reason_codes tests/test_liepin_pi_executor.py::test_card_envelope_preserves_opencli_safe_reason_code tests/test_pi_external_agent.py::test_pi_prompt_can_describe_opencli_backend_without_dokobot_wording -q
```

Expected: pass.

## Task 1: Add OpenCLI Dependency And Settings

**Files:**
- Modify: `apps/web-svelte/package.json`
- Modify: `apps/web-svelte/bun.lock`
- Modify: `src/seektalent/config.py`
- Modify: `src/seektalent/default.env`
- Modify: `.env.example`
- Test: `tests/test_liepin_config.py`

- [ ] **Step 1: Write failing settings tests**

Add to `tests/test_liepin_config.py`:

```python
def test_liepin_opencli_backend_defaults_to_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEEKTALENT_LIEPIN_WORKER_MODE", "disabled")
    monkeypatch.delenv("SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND", raising=False)

    settings = AppSettings()

    assert settings.liepin_browser_action_backend == "disabled"
    assert settings.liepin_opencli_command == "apps/web-svelte/node_modules/.bin/opencli"
    assert settings.liepin_opencli_session == "seektalent-liepin"
    assert settings.liepin_opencli_allowed_hosts == ("www.liepin.com", "h.liepin.com", "c.liepin.com", "lpt.liepin.com")
    assert settings.liepin_opencli_allowed_start_urls == ("https://www.liepin.com/zhaopin/",)
    assert settings.liepin_opencli_max_actions_per_task == 80
    assert settings.liepin_opencli_max_pages_per_task == 1
    assert settings.liepin_opencli_max_cards_per_task == 20


def test_liepin_opencli_backend_validates_json_and_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEEKTALENT_LIEPIN_WORKER_MODE", "disabled")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND", "opencli")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_OPENCLI_ALLOWED_HOSTS_JSON", '["www.liepin.com"]')
    monkeypatch.setenv("SEEKTALENT_LIEPIN_OPENCLI_ALLOWED_START_URLS_JSON", '["https://www.liepin.com/zhaopin/"]')
    monkeypatch.setenv("SEEKTALENT_LIEPIN_OPENCLI_MAX_ACTIONS_PER_TASK", "12")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_OPENCLI_MAX_PAGES_PER_TASK", "1")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_OPENCLI_MAX_CARDS_PER_TASK", "10")

    settings = AppSettings()

    assert settings.liepin_browser_action_backend == "opencli"
    assert settings.liepin_opencli_allowed_hosts == ("www.liepin.com",)
    assert settings.liepin_opencli_allowed_start_urls == ("https://www.liepin.com/zhaopin/",)
    assert settings.liepin_opencli_max_actions_per_task == 12
    assert settings.liepin_opencli_max_pages_per_task == 1
    assert settings.liepin_opencli_max_cards_per_task == 10


def test_liepin_opencli_backend_rejects_empty_start_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEEKTALENT_LIEPIN_WORKER_MODE", "disabled")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND", "opencli")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_OPENCLI_ALLOWED_START_URLS_JSON", "[]")

    with pytest.raises(ValueError, match="liepin_opencli_allowed_start_urls_json must not be empty"):
        AppSettings()


def test_liepin_opencli_command_resolves_from_workspace_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / "workspace"
    binary = workspace / "apps/web-svelte/node_modules/.bin/opencli"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setenv("SEEKTALENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("SEEKTALENT_LIEPIN_WORKER_MODE", "disabled")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND", "opencli")

    settings = AppSettings()

    assert settings.liepin_opencli_command_argv == (str(binary),)


def test_liepin_opencli_empty_command_uses_default_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEEKTALENT_LIEPIN_WORKER_MODE", "disabled")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND", "disabled")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_OPENCLI_COMMAND", "")

    settings = AppSettings()

    assert settings.liepin_opencli_command == "apps/web-svelte/node_modules/.bin/opencli"
```

- [ ] **Step 2: Run focused tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_liepin_config.py::test_liepin_opencli_backend_defaults_to_disabled tests/test_liepin_config.py::test_liepin_opencli_backend_validates_json_and_budget tests/test_liepin_config.py::test_liepin_opencli_backend_rejects_empty_start_urls tests/test_liepin_config.py::test_liepin_opencli_command_resolves_from_workspace_root tests/test_liepin_config.py::test_liepin_opencli_empty_command_uses_default_when_disabled -q
```

Expected: fail because OpenCLI settings do not exist.

- [ ] **Step 3: Add settings fields**

In `src/seektalent/config.py`, add these `AppSettings` fields near the existing Liepin Pi settings:

```python
liepin_browser_action_backend: str = "disabled"
liepin_opencli_command: str = "apps/web-svelte/node_modules/.bin/opencli"
liepin_opencli_session: str = "seektalent-liepin"
liepin_opencli_allowed_hosts_json: str = '["www.liepin.com","h.liepin.com","c.liepin.com","lpt.liepin.com"]'
liepin_opencli_allowed_start_urls_json: str = '["https://www.liepin.com/zhaopin/"]'
liepin_opencli_max_actions_per_task: int = 80
liepin_opencli_max_pages_per_task: int = 1
liepin_opencli_max_cards_per_task: int = 20
liepin_opencli_timeout_seconds: int = 20
```

Add validators/properties:

```python
@field_validator("liepin_browser_action_backend", mode="before")
@classmethod
def normalize_liepin_browser_action_backend(cls, value: str | None) -> str:
    return (value or "disabled").strip().lower() or "disabled"

@field_validator("liepin_opencli_command", mode="before")
@classmethod
def normalize_liepin_opencli_command(cls, value: str | None) -> str:
    text = (value or "").strip()
    return text or "apps/web-svelte/node_modules/.bin/opencli"

@field_validator("liepin_opencli_session", mode="before")
@classmethod
def normalize_liepin_opencli_session(cls, value: str | None) -> str:
    text = (value or "").strip()
    return text or "seektalent-liepin"

@property
def liepin_opencli_allowed_hosts(self) -> tuple[str, ...]:
    return _json_string_tuple(self.liepin_opencli_allowed_hosts_json, field_name="liepin_opencli_allowed_hosts_json")

@property
def liepin_opencli_allowed_start_urls(self) -> tuple[str, ...]:
    return _json_string_tuple(
        self.liepin_opencli_allowed_start_urls_json,
        field_name="liepin_opencli_allowed_start_urls_json",
    )

@property
def liepin_opencli_command_argv(self) -> tuple[str, ...]:
    argv = tuple(shlex.split(self.liepin_opencli_command))
    if not argv:
        return (str(self.resolve_workspace_path("apps/web-svelte/node_modules/.bin/opencli")),)
    command = Path(argv[0])
    if not command.is_absolute():
        command = self.resolve_workspace_path(str(command))
    return (str(command), *argv[1:])
```

Ensure `Path` and `shlex` are imported in `src/seektalent/config.py`:

```python
from pathlib import Path
import shlex
```

In the existing range/config validation path, add:

```python
if self.liepin_browser_action_backend not in {"disabled", "opencli"}:
    raise ValueError("liepin_browser_action_backend must be disabled or opencli")
if self.liepin_browser_action_backend == "opencli":
    if not self.liepin_opencli_command_argv:
        raise ValueError("liepin_opencli_command must not be empty")
    if not self.liepin_opencli_allowed_hosts:
        raise ValueError("liepin_opencli_allowed_hosts_json must not be empty")
    if not self.liepin_opencli_allowed_start_urls:
        raise ValueError("liepin_opencli_allowed_start_urls_json must not be empty")
if min(
    self.liepin_opencli_max_actions_per_task,
    self.liepin_opencli_max_pages_per_task,
    self.liepin_opencli_max_cards_per_task,
    self.liepin_opencli_timeout_seconds,
) < 1:
    raise ValueError("OpenCLI Liepin budgets and timeout must be >= 1")
```

- [ ] **Step 4: Add env defaults**

Add to `src/seektalent/default.env` and `.env.example`:

```dotenv
# Liepin browser action backend. OpenCLI CLI is installed by project dependencies; the Chrome extension is installed by the user.
SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND=disabled
SEEKTALENT_LIEPIN_OPENCLI_COMMAND=apps/web-svelte/node_modules/.bin/opencli
SEEKTALENT_LIEPIN_OPENCLI_SESSION=seektalent-liepin
SEEKTALENT_LIEPIN_OPENCLI_ALLOWED_HOSTS_JSON=["www.liepin.com","h.liepin.com","c.liepin.com","lpt.liepin.com"]
SEEKTALENT_LIEPIN_OPENCLI_ALLOWED_START_URLS_JSON=["https://www.liepin.com/zhaopin/"]
SEEKTALENT_LIEPIN_OPENCLI_MAX_ACTIONS_PER_TASK=80
SEEKTALENT_LIEPIN_OPENCLI_MAX_PAGES_PER_TASK=1
SEEKTALENT_LIEPIN_OPENCLI_MAX_CARDS_PER_TASK=20
SEEKTALENT_LIEPIN_OPENCLI_TIMEOUT_SECONDS=20
```

- [ ] **Step 5: Add OpenCLI dependency**

In `apps/web-svelte/package.json`, add to `"dependencies"`:

```json
"@jackwener/opencli": "1.8.0",
"typebox": "1.1.38"
```

Run:

```bash
cd apps/web-svelte && bun install
```

Expected: `apps/web-svelte/bun.lock` updates and `apps/web-svelte/node_modules/.bin/opencli` exists.

- [ ] **Step 5A: Document the distribution boundary explicitly**

This slice makes OpenCLI automatic for source/dev workspaces through `apps/web-svelte` dependencies and `scripts/start-dev-workbench.sh`.

Do not claim PyPI installs automatically include OpenCLI until the package/installer has one of these explicit mechanisms:

- bundles the built Svelte dependency tree including `node_modules/.bin/opencli`;
- runs a first-run dependency bootstrap before enabling OpenCLI mode;
- ships a separate desktop/local-app installer that installs the Node dependency tree.

For current Python-only package paths, OpenCLI mode must fail closed with `liepin_opencli_command_missing` when `apps/web-svelte/node_modules/.bin/opencli` is absent.

Add this to `README.md` and `docs/configuration.md` so the packaging behavior is explicit rather than implicit.

- [ ] **Step 6: Re-run focused tests**

Run:

```bash
uv run pytest tests/test_liepin_config.py::test_liepin_opencli_backend_defaults_to_disabled tests/test_liepin_config.py::test_liepin_opencli_backend_validates_json_and_budget tests/test_liepin_config.py::test_liepin_opencli_backend_rejects_empty_start_urls tests/test_liepin_config.py::test_liepin_opencli_command_resolves_from_workspace_root tests/test_liepin_config.py::test_liepin_opencli_empty_command_uses_default_when_disabled -q
```

Expected: pass.

## Task 2: Build The Restricted OpenCLI Helper

**Files:**
- Create: `src/seektalent/providers/pi_agent/opencli_browser.py`
- Test: `tests/test_pi_opencli_browser.py`

- [ ] **Step 1: Write failing helper tests**

Create `tests/test_pi_opencli_browser.py`:

```python
from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence

import pytest

from seektalent.providers.pi_agent.opencli_browser import (
    OpenCliBrowserConfig,
    OpenCliBrowserError,
    OpenCliBrowserRunner,
    bucket_text,
    classify_liepin_state,
    default_liepin_opencli_policy,
)


class FakeCommands:
    def __init__(self, *, outputs: dict[tuple[str, ...], str] | None = None, fail: bool = False) -> None:
        self.outputs = outputs or {}
        self.fail = fail
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv: Sequence[str], *, timeout: int) -> str:
        del timeout
        call = tuple(argv)
        self.calls.append(call)
        if self.fail:
            raise subprocess.TimeoutExpired(cmd=list(argv), timeout=1)
        return self.outputs.get(call, "{}")


def _runner(commands: FakeCommands) -> OpenCliBrowserRunner:
    return OpenCliBrowserRunner(
        config=OpenCliBrowserConfig(
            command=("opencli",),
            session="seektalent-liepin",
            timeout_seconds=10,
            policy=default_liepin_opencli_policy(
                allowed_hosts=("www.liepin.com",),
                allowed_start_urls=("https://www.liepin.com/zhaopin/",),
            ),
        ),
        commands=commands,
    )


def test_status_maps_opencli_doctor_success() -> None:
    commands = FakeCommands(outputs={("opencli", "doctor"): "Everything looks good!"})
    result = _runner(commands).status()

    assert result.ok is True
    assert result.safe_reason_code == "configured"
    assert commands.calls == [("opencli", "doctor")]


def test_open_liepin_tab_rejects_wrong_host_before_opencli_call() -> None:
    commands = FakeCommands()
    with pytest.raises(OpenCliBrowserError) as error:
        _runner(commands).open_liepin_tab("https://example.com/")

    assert error.value.safe_reason_code == "liepin_opencli_host_blocked"
    assert commands.calls == []


def test_open_liepin_tab_rejects_unapproved_start_url() -> None:
    commands = FakeCommands()
    with pytest.raises(OpenCliBrowserError) as error:
        _runner(commands).open_liepin_tab("https://www.liepin.com/")

    assert error.value.safe_reason_code == "liepin_opencli_start_url_blocked"
    assert commands.calls == []


def test_open_liepin_tab_reuses_existing_liepin_tab_before_creating_new_one() -> None:
    commands = FakeCommands(
        outputs={
            ("opencli", "browser", "seektalent-liepin", "tab", "list"): '[{"id":"tab-1","url":"https://www.liepin.com/zhaopin/"}]',
            ("opencli", "browser", "seektalent-liepin", "tab", "select", "tab-1"): "{}",
        }
    )

    result = _runner(commands).open_liepin_tab("https://www.liepin.com/zhaopin/")

    assert result.ok is True
    assert commands.calls == [
        ("opencli", "browser", "seektalent-liepin", "tab", "list"),
        ("opencli", "browser", "seektalent-liepin", "tab", "select", "tab-1"),
    ]


def test_open_liepin_tab_uses_tab_new_when_no_owned_tab_exists() -> None:
    commands = FakeCommands(
        outputs={
            ("opencli", "browser", "seektalent-liepin", "tab", "list"): "[]",
            ("opencli", "browser", "seektalent-liepin", "tab", "new", "https://www.liepin.com/zhaopin/"): "{}",
        }
    )

    result = _runner(commands).open_liepin_tab("https://www.liepin.com/zhaopin/")

    assert result.ok is True
    assert commands.calls == [
        ("opencli", "browser", "seektalent-liepin", "tab", "list"),
        ("opencli", "browser", "seektalent-liepin", "tab", "new", "https://www.liepin.com/zhaopin/"),
    ]


def test_fill_rejects_long_or_sensitive_text() -> None:
    commands = FakeCommands()
    with pytest.raises(OpenCliBrowserError) as error:
        _runner(commands).fill(target="16", text="x" * 81)

    assert error.value.safe_reason_code == "liepin_opencli_forbidden_text"
    assert commands.calls == []


def test_fill_allows_short_keyword_text() -> None:
    commands = FakeCommands(outputs={("opencli", "browser", "seektalent-liepin", "fill", "16", "数据开发专家"): '{"filled":true}'})

    result = _runner(commands).fill(target="16", text="数据开发专家")

    assert result.ok is True
    assert commands.calls == [("opencli", "browser", "seektalent-liepin", "fill", "16", "数据开发专家")]


def test_forbidden_opencli_command_is_rejected() -> None:
    commands = FakeCommands()
    with pytest.raises(OpenCliBrowserError) as error:
        _runner(commands)._run_browser_command("eval", ("document.cookie",))

    assert error.value.safe_reason_code == "liepin_opencli_forbidden_command"
    assert commands.calls == []


def test_public_payload_does_not_include_raw_output() -> None:
    commands = FakeCommands(
        outputs={
            ("opencli", "browser", "seektalent-liepin", "get", "url"): "https://www.liepin.com/zhaopin/",
            ("opencli", "browser", "seektalent-liepin", "state"): "搜索职位、公司 [ref=16]",
        }
    )

    result = _runner(commands).state()

    payload = result.to_public_payload()
    assert payload == {"ok": True, "action": "state", "safeReasonCode": "configured", "counts": {}}
    assert "搜索职位" not in json.dumps(payload, ensure_ascii=False)


def test_state_rejects_sensitive_observation() -> None:
    commands = FakeCommands(
        outputs={
            ("opencli", "browser", "seektalent-liepin", "get", "url"): "https://www.liepin.com/zhaopin/",
            ("opencli", "browser", "seektalent-liepin", "state"): "document.cookie=secret",
        }
    )

    with pytest.raises(OpenCliBrowserError) as error:
        _runner(commands).state()

    assert error.value.safe_reason_code == "liepin_opencli_malformed_state"


def test_state_classifier_blocks_login_and_risk_pages_before_next_action() -> None:
    assert classify_liepin_state(url="https://www.liepin.com/zhaopin/", text="请登录后继续") == (
        "liepin_opencli_login_required"
    )
    assert classify_liepin_state(url="https://www.liepin.com/zhaopin/", text="安全验证 请完成验证码") == (
        "liepin_opencli_risk_page"
    )
    assert classify_liepin_state(url="https://lpt.liepin.com/", text="请选择招聘身份") == (
        "liepin_opencli_identity_intercept"
    )


def test_state_returns_terminal_classification_to_pi_payload_only() -> None:
    commands = FakeCommands(
        outputs={
            ("opencli", "browser", "seektalent-liepin", "get", "url"): "https://www.liepin.com/zhaopin/",
            ("opencli", "browser", "seektalent-liepin", "state"): "请登录后继续 [ref=login]",
        }
    )

    result = _runner(commands).state()

    assert result.ok is False
    assert result.safe_reason_code == "liepin_opencli_login_required"
    pi_payload = result.to_pi_tool_payload()
    assert pi_payload["observation"]["terminal"] is True
    public_payload = result.to_public_payload()
    assert "请登录" not in json.dumps(public_payload, ensure_ascii=False)


def test_state_returns_bounded_observation_to_pi_only() -> None:
    commands = FakeCommands(
        outputs={
            ("opencli", "browser", "seektalent-liepin", "get", "url"): "https://www.liepin.com/zhaopin/",
            ("opencli", "browser", "seektalent-liepin", "state"): "搜索职位、公司 [ref=16]",
        }
    )

    result = _runner(commands).state()

    pi_payload = result.to_pi_tool_payload()
    public_payload = result.to_public_payload()
    assert pi_payload["observation"]["text"] == "搜索职位、公司 [ref=16]"
    assert pi_payload["observation"]["terminal"] is False
    assert "搜索职位" not in json.dumps(public_payload, ensure_ascii=False)


def test_bucket_text_is_count_only() -> None:
    assert bucket_text("数据开发专家") == {"chars": 6}
```

- [ ] **Step 2: Run helper tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_pi_opencli_browser.py -q
```

Expected: fail because `opencli_browser.py` does not exist.

- [ ] **Step 3: Implement `opencli_browser.py`**

Create `src/seektalent/providers/pi_agent/opencli_browser.py`:

```python
from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urlparse


ALLOWED_BROWSER_COMMANDS = frozenset({"state", "get", "find", "click", "fill", "scroll", "wait", "tab"})
FORBIDDEN_BROWSER_COMMANDS = frozenset({"eval", "network", "upload", "console", "dialog", "drag", "select"})


class OpenCliCommandRunner(Protocol):
    def run(self, argv: Sequence[str], *, timeout: int) -> str: ...


@dataclass(frozen=True)
class SubprocessOpenCliCommandRunner:
    def run(self, argv: Sequence[str], *, timeout: int) -> str:
        completed = subprocess.run(
            list(argv),
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return completed.stdout


@dataclass(frozen=True)
class OpenCliBrowserPolicy:
    source_kind: str
    allowed_hosts: tuple[str, ...]
    allowed_start_urls: tuple[str, ...]
    max_keyword_chars: int = 80


@dataclass(frozen=True)
class OpenCliBrowserConfig:
    command: tuple[str, ...]
    session: str
    timeout_seconds: int
    policy: OpenCliBrowserPolicy


@dataclass(frozen=True)
class OpenCliBrowserResult:
    ok: bool
    action: str
    safe_reason_code: str = "configured"
    counts: Mapping[str, int] = field(default_factory=dict)
    observation: Mapping[str, object] = field(default_factory=dict)
    private_output: str = ""

    def to_public_payload(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "action": self.action,
            "safeReasonCode": self.safe_reason_code,
            "counts": dict(self.counts),
        }

    def to_pi_tool_payload(self) -> dict[str, object]:
        payload = self.to_public_payload()
        if self.observation:
            payload["observation"] = dict(self.observation)
        return payload


class OpenCliBrowserError(RuntimeError):
    def __init__(self, safe_reason_code: str) -> None:
        super().__init__(safe_reason_code)
        self.safe_reason_code = safe_reason_code


def default_liepin_opencli_policy(
    *,
    allowed_hosts: tuple[str, ...],
    allowed_start_urls: tuple[str, ...],
) -> OpenCliBrowserPolicy:
    return OpenCliBrowserPolicy(
        source_kind="liepin",
        allowed_hosts=allowed_hosts,
        allowed_start_urls=allowed_start_urls,
    )


def bucket_text(text: str) -> dict[str, int]:
    return {"chars": len(text)}


def build_observation(text: str, *, max_chars: int = 12000) -> dict[str, object]:
    if _looks_sensitive(text):
        raise OpenCliBrowserError("liepin_opencli_malformed_state")
    return {
        "text": text[:max_chars],
        "chars": len(text),
        "truncated": len(text) > max_chars,
    }


def classify_liepin_state(*, url: str, text: str) -> str | None:
    host = urlparse(url).hostname or ""
    lowered = text.lower()
    if host not in {"www.liepin.com", "h.liepin.com", "c.liepin.com", "lpt.liepin.com"}:
        return "liepin_opencli_host_blocked"
    if host == "lpt.liepin.com" and ("身份" in text or "请选择" in text):
        return "liepin_opencli_identity_intercept"
    if "登录" in text or "login" in lowered:
        return "liepin_opencli_login_required"
    if "验证码" in text or "安全验证" in text or "risk" in lowered or "captcha" in lowered:
        return "liepin_opencli_risk_page"
    if any(marker in text for marker in ("联系", "聊天", "下载", "付费", "购买")):
        return "liepin_opencli_unknown_modal"
    return None


def _looks_sensitive(text: str) -> bool:
    lowered = text.lower()
    forbidden = (
        "document.cookie",
        "localstorage",
        "sessionstorage",
        "authorization:",
        "bearer ",
        "storagestate",
        "<script",
        "<html",
    )
    return any(marker in lowered for marker in forbidden)


class OpenCliBrowserRunner:
    def __init__(
        self,
        *,
        config: OpenCliBrowserConfig,
        commands: OpenCliCommandRunner | None = None,
    ) -> None:
        self._config = config
        self._commands = commands or SubprocessOpenCliCommandRunner()

    def status(self) -> OpenCliBrowserResult:
        try:
            self._run(tuple(self._config.command) + ("doctor",))
        except OpenCliBrowserError as exc:
            return OpenCliBrowserResult(ok=False, action="status", safe_reason_code=exc.safe_reason_code)
        return OpenCliBrowserResult(ok=True, action="status")

    def open_liepin_tab(self, url: str) -> OpenCliBrowserResult:
        self._validate_start_url(url)
        tabs = self._list_tabs()
        for tab in tabs:
            if tab.get("url") == url and isinstance(tab.get("id"), str):
                output = self._run_browser_command("tab", ("select", tab["id"]))
                return OpenCliBrowserResult(ok=True, action="open_liepin_tab", private_output=output)
        output = self._run_browser_command("tab", ("new", url))
        return OpenCliBrowserResult(ok=True, action="open_liepin_tab", private_output=output)

    def state(self) -> OpenCliBrowserResult:
        current_url = self._current_url()
        output = self._run_browser_command("state", ())
        observation = build_observation(output)
        terminal_reason = classify_liepin_state(url=current_url, text=output)
        observation["terminal"] = terminal_reason is not None
        if terminal_reason:
            return OpenCliBrowserResult(
                ok=False,
                action="state",
                safe_reason_code=terminal_reason,
                observation=observation,
                private_output=output,
            )
        return OpenCliBrowserResult(ok=True, action="state", observation=observation, private_output=output)

    def get_url(self) -> OpenCliBrowserResult:
        output = self._run_browser_command("get", ("url",))
        return OpenCliBrowserResult(ok=True, action="get_url", observation=build_observation(output), private_output=output)

    def find(self, *, query: str) -> OpenCliBrowserResult:
        self._validate_keyword_text(query)
        output = self._run_browser_command("find", (query,))
        return OpenCliBrowserResult(ok=True, action="find", observation=build_observation(output), private_output=output)

    def fill(self, *, target: str, text: str) -> OpenCliBrowserResult:
        self._validate_keyword_text(text)
        output = self._run_browser_command("fill", (target, text))
        return OpenCliBrowserResult(ok=True, action="fill", counts=bucket_text(text), private_output=output)

    def click(self, *, target: str) -> OpenCliBrowserResult:
        output = self._run_browser_command("click", (target,))
        return OpenCliBrowserResult(ok=True, action="click", private_output=output)

    def scroll(self, *, direction: str) -> OpenCliBrowserResult:
        if direction not in {"up", "down"}:
            raise OpenCliBrowserError("liepin_opencli_forbidden_command")
        output = self._run_browser_command("scroll", (direction,))
        return OpenCliBrowserResult(ok=True, action="scroll", private_output=output)

    def wait_time(self, *, seconds: int) -> OpenCliBrowserResult:
        if seconds < 1 or seconds > 10:
            raise OpenCliBrowserError("liepin_opencli_forbidden_command")
        output = self._run_browser_command("wait", ("time", str(seconds)))
        return OpenCliBrowserResult(ok=True, action="wait_time", private_output=output)

    def _list_tabs(self) -> list[dict[str, object]]:
        output = self._run_browser_command("tab", ("list",))
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError as exc:
            raise OpenCliBrowserError("liepin_opencli_malformed_state") from exc
        if not isinstance(parsed, list):
            raise OpenCliBrowserError("liepin_opencli_malformed_state")
        return [tab for tab in parsed if isinstance(tab, dict)]

    def _current_url(self) -> str:
        return self._run_browser_command("get", ("url",)).strip()

    def _run_browser_command(self, command: str, args: tuple[str, ...]) -> str:
        if command not in ALLOWED_BROWSER_COMMANDS or command in FORBIDDEN_BROWSER_COMMANDS:
            raise OpenCliBrowserError("liepin_opencli_forbidden_command")
        self._validate_command_shape(command, args)
        argv = tuple(self._config.command) + ("browser", self._config.session, command, *args)
        return self._run(argv)

    def _validate_command_shape(self, command: str, args: tuple[str, ...]) -> None:
        valid = {
            "state": len(args) == 0,
            "get": args == ("url",),
            "find": len(args) == 1,
            "click": len(args) == 1,
            "fill": len(args) == 2,
            "scroll": args in {("up",), ("down",)},
            "wait": len(args) == 2 and args[0] in {"time", "text", "selector"},
            "tab": (
                args == ("list",)
                or (len(args) == 2 and args[0] in {"new", "select"} and bool(args[1].strip()))
            ),
        }.get(command, False)
        if not valid:
            raise OpenCliBrowserError("liepin_opencli_forbidden_command")

    def _run(self, argv: tuple[str, ...]) -> str:
        try:
            return self._commands.run(argv, timeout=self._config.timeout_seconds)
        except FileNotFoundError as exc:
            raise OpenCliBrowserError("liepin_opencli_command_missing") from exc
        except subprocess.TimeoutExpired as exc:
            raise OpenCliBrowserError("liepin_opencli_timeout") from exc
        except subprocess.CalledProcessError as exc:
            output = f"{exc.stdout or ''}\n{exc.stderr or ''}"
            if "Extension" in output and ("not connected" in output or "disconnected" in output):
                raise OpenCliBrowserError("liepin_opencli_extension_disconnected") from exc
            raise OpenCliBrowserError("liepin_opencli_status_unavailable") from exc

    def _validate_start_url(self, url: str) -> None:
        host = urlparse(url).hostname or ""
        if host not in self._config.policy.allowed_hosts:
            raise OpenCliBrowserError("liepin_opencli_host_blocked")
        if url not in self._config.policy.allowed_start_urls:
            raise OpenCliBrowserError("liepin_opencli_start_url_blocked")

    def _validate_keyword_text(self, text: str) -> None:
        if not text.strip() or len(text) > self._config.policy.max_keyword_chars:
            raise OpenCliBrowserError("liepin_opencli_forbidden_text")
        forbidden_fragments = ("cookie", "Authorization", "Bearer", "storageState", "\n", "\r", "\x00")
        if any(fragment in text for fragment in forbidden_fragments):
            raise OpenCliBrowserError("liepin_opencli_forbidden_text")


def result_from_json_line(text: str) -> OpenCliBrowserResult:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OpenCliBrowserError("liepin_opencli_malformed_state") from exc
    if not isinstance(payload, dict):
        raise OpenCliBrowserError("liepin_opencli_malformed_state")
    return OpenCliBrowserResult(ok=True, action="parse", counts={})
```

- [ ] **Step 4: Re-run helper tests**

Run:

```bash
uv run pytest tests/test_pi_opencli_browser.py -q
```

Expected: pass.

## Task 3: Add The OpenCLI Helper CLI

**Files:**
- Create: `src/seektalent/providers/pi_agent/opencli_browser_cli.py`
- Test: `tests/test_pi_opencli_browser.py`

- [ ] **Step 1: Add CLI tests**

Append to `tests/test_pi_opencli_browser.py`:

```python
def test_cli_rejects_unknown_action(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["opencli_browser_cli", "network"])
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))

    rc = opencli_browser_cli.main()

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["safeReasonCode"] == "liepin_opencli_forbidden_command"


def test_cli_state_returns_pi_observation(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    commands = FakeCommands(
        outputs={
            ("opencli", "browser", "seektalent-liepin", "get", "url"): "https://www.liepin.com/zhaopin/",
            ("opencli", "browser", "seektalent-liepin", "state"): "搜索职位、公司 [ref=16]",
        }
    )
    monkeypatch.setattr("sys.argv", ["opencli_browser_cli", "state"])
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    monkeypatch.setattr(opencli_browser_cli, "_runner_from_env", lambda: _runner(commands))

    rc = opencli_browser_cli.main()

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["observation"]["text"] == "搜索职位、公司 [ref=16]"


def test_cli_runner_uses_shell_safe_command_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEEKTALENT_LIEPIN_OPENCLI_COMMAND", '"/tmp/open cli" --profile "qa user"')

    runner = opencli_browser_cli._runner_from_env()

    assert runner._config.command == ("/tmp/open cli", "--profile", "qa user")
```

Also add these imports at the top of the file:

```python
import io
from seektalent.providers.pi_agent import opencli_browser_cli
```

- [ ] **Step 2: Run CLI test and confirm it fails**

Run:

```bash
uv run pytest tests/test_pi_opencli_browser.py::test_cli_rejects_unknown_action -q
```

Expected: fail because the CLI module does not exist.

- [ ] **Step 3: Implement CLI**

Create `src/seektalent/providers/pi_agent/opencli_browser_cli.py`:

```python
from __future__ import annotations

import json
import os
import shlex
import sys

from seektalent.providers.pi_agent.opencli_browser import (
    OpenCliBrowserConfig,
    OpenCliBrowserError,
    OpenCliBrowserResult,
    OpenCliBrowserRunner,
    default_liepin_opencli_policy,
)


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        _print(OpenCliBrowserResult(ok=False, action=action or "unknown", safe_reason_code="liepin_opencli_malformed_state"))
        return 1
    if not isinstance(payload, dict):
        _print(OpenCliBrowserResult(ok=False, action=action or "unknown", safe_reason_code="liepin_opencli_malformed_state"))
        return 1
    runner = _runner_from_env()
    try:
        result = _run_action(runner, action, payload)
    except OpenCliBrowserError as exc:
        result = OpenCliBrowserResult(ok=False, action=action or "unknown", safe_reason_code=exc.safe_reason_code)
    _print(result)
    return 0 if result.ok else 1


def _runner_from_env() -> OpenCliBrowserRunner:
    command = tuple(shlex.split(os.environ.get("SEEKTALENT_LIEPIN_OPENCLI_COMMAND") or "apps/web-svelte/node_modules/.bin/opencli"))
    allowed_hosts = _json_tuple(os.environ.get("SEEKTALENT_LIEPIN_OPENCLI_ALLOWED_HOSTS_JSON"), default=("www.liepin.com",))
    allowed_start_urls = _json_tuple(os.environ.get("SEEKTALENT_LIEPIN_OPENCLI_ALLOWED_START_URLS_JSON"), default=("https://www.liepin.com/zhaopin/",))
    return OpenCliBrowserRunner(
        config=OpenCliBrowserConfig(
            command=command,
            session=os.environ.get("SEEKTALENT_LIEPIN_OPENCLI_SESSION") or "seektalent-liepin",
            timeout_seconds=int(os.environ.get("SEEKTALENT_LIEPIN_OPENCLI_TIMEOUT_SECONDS") or "20"),
            policy=default_liepin_opencli_policy(
                allowed_hosts=allowed_hosts,
                allowed_start_urls=allowed_start_urls,
            ),
        )
    )


def _run_action(runner: OpenCliBrowserRunner, action: str, payload: dict[str, object]) -> OpenCliBrowserResult:
    if action == "status":
        return runner.status()
    if action == "open_liepin_tab":
        return runner.open_liepin_tab(str(payload.get("url") or ""))
    if action == "state":
        return runner.state()
    if action == "get_url":
        return runner.get_url()
    if action == "find":
        return runner.find(query=str(payload.get("query") or ""))
    if action == "fill":
        return runner.fill(target=str(payload.get("target") or ""), text=str(payload.get("text") or ""))
    if action == "click":
        return runner.click(target=str(payload.get("target") or ""))
    if action == "scroll":
        return runner.scroll(direction=str(payload.get("direction") or ""))
    if action == "wait_time":
        return runner.wait_time(seconds=int(payload.get("seconds") or 1))
    raise OpenCliBrowserError("liepin_opencli_forbidden_command")


def _json_tuple(value: str | None, *, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    loaded = json.loads(value)
    if not isinstance(loaded, list) or not all(isinstance(item, str) and item for item in loaded):
        raise OpenCliBrowserError("liepin_opencli_malformed_state")
    return tuple(loaded)


def _print(result: OpenCliBrowserResult) -> None:
    print(json.dumps(result.to_pi_tool_payload(), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Re-run CLI tests**

Run:

```bash
uv run pytest tests/test_pi_opencli_browser.py::test_cli_rejects_unknown_action -q
```

Expected: pass.

## Task 4: Register Pi OpenCLI Tools

**Files:**
- Create: `src/seektalent/providers/pi_agent/pi_extensions/seektalent_opencli_browser.ts`
- Test: `tests/test_pi_external_agent.py`

- [ ] **Step 1: Add extension text tests**

Add to `tests/test_pi_external_agent.py`:

```python
def test_opencli_pi_extension_exposes_only_restricted_tools() -> None:
    text = Path("src/seektalent/providers/pi_agent/pi_extensions/seektalent_opencli_browser.ts").read_text(encoding="utf-8")

    assert "seektalent_opencli_status" in text
    assert "seektalent_opencli_capabilities" in text
    assert "seektalent_opencli_state" in text
    assert "seektalent_opencli_open_liepin_tab" in text
    assert "seektalent_opencli_get_url" in text
    assert "seektalent_opencli_find" in text
    assert "seektalent_opencli_fill" in text
    assert "seektalent_opencli_click" in text
    assert "seektalent_opencli_scroll" in text
    assert "seektalent_opencli_wait_time" in text
    assert "browser eval" not in text
    assert "browser network" not in text
    assert "document.cookie" not in text
    assert "child.stderr.on" in text
    assert "MAX_OUTPUT_CHARS" in text
    assert "terminalReason" in text
    assert 'import type { ExtensionAPI } from "@earendil-works/pi-coding-agent"' in text
    assert ("type " + "ExtensionAPI = {") not in text
    assert "async execute(_toolCallId, params" in text
    assert "stateReady" in text
    assert "requires a fresh non-terminal state" in text
    assert "details: {}" in text
```

Ensure `Path` is imported:

```python
from pathlib import Path
```

- [ ] **Step 2: Run extension test and confirm it fails**

Run:

```bash
uv run pytest tests/test_pi_external_agent.py::test_opencli_pi_extension_exposes_only_restricted_tools -q
```

Expected: fail because the extension file does not exist.

- [ ] **Step 3: Create extension**

Create `src/seektalent/providers/pi_agent/pi_extensions/seektalent_opencli_browser.ts`:

```ts
import { spawn } from "node:child_process";
import { Type } from "typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const PYTHON = process.env.SEEKTALENT_PYTHON || "python";
const HELPER_MODULE = "seektalent.providers.pi_agent.opencli_browser_cli";
const TIMEOUT_MS = Number(process.env.SEEKTALENT_LIEPIN_OPENCLI_TOOL_TIMEOUT_MS || "25000");
const MAX_OUTPUT_CHARS = Number(process.env.SEEKTALENT_LIEPIN_OPENCLI_MAX_OUTPUT_CHARS || "120000");
let actionCount = 0;
let terminalReason: string | null = null;
let stateReady = false;
const maxActions = Number(process.env.SEEKTALENT_LIEPIN_OPENCLI_MAX_ACTIONS_PER_TASK || "80");
const MUTATING_ACTIONS = new Set(["fill", "click", "scroll"]);

function textResult(payload: string) {
  return { content: [{ type: "text" as const, text: payload }], details: {} };
}

function runAction(action: string, payload: Record<string, unknown>): Promise<string> {
  if (action === "open_liepin_tab") {
    actionCount = 0;
    terminalReason = null;
    stateReady = false;
  }
  if (!["status", "capabilities", "state", "get_url"].includes(action) && terminalReason) {
    return Promise.resolve(JSON.stringify({ ok: false, action, safeReasonCode: terminalReason, counts: {} }));
  }
  if (MUTATING_ACTIONS.has(action) && !stateReady) {
    return Promise.resolve(JSON.stringify({
      ok: false,
      action,
      safeReasonCode: "liepin_opencli_malformed_state",
      safeMessage: "requires a fresh non-terminal state",
      counts: {}
    }));
  }
  if (action !== "status" && action !== "capabilities") {
    actionCount += 1;
    if (actionCount > maxActions) {
      return Promise.resolve(JSON.stringify({ ok: false, action, safeReasonCode: "liepin_opencli_budget_exhausted", counts: {} }));
    }
  }
  if (MUTATING_ACTIONS.has(action)) {
    stateReady = false;
  }
  return new Promise((resolve) => {
    const child = spawn(PYTHON, ["-m", HELPER_MODULE, action], {
      stdio: ["pipe", "pipe", "pipe"],
      env: process.env,
    });
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      resolve(JSON.stringify({ ok: false, action, safeReasonCode: "liepin_opencli_timeout", counts: {} }));
    }, TIMEOUT_MS);
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += String(chunk);
      if (stdout.length > MAX_OUTPUT_CHARS) {
        child.kill("SIGKILL");
        resolve(JSON.stringify({ ok: false, action, safeReasonCode: "liepin_opencli_malformed_state", counts: {} }));
      }
    });
    child.stderr.on("data", (chunk) => {
      stderr = (stderr + String(chunk)).slice(0, 4096);
    });
    child.on("error", () => {
      clearTimeout(timer);
      resolve(JSON.stringify({ ok: false, action, safeReasonCode: "liepin_opencli_status_unavailable", counts: {} }));
    });
    child.on("close", () => {
      clearTimeout(timer);
      const text = stdout.trim() || JSON.stringify({ ok: false, action, safeReasonCode: "liepin_opencli_status_unavailable", counts: {} });
      if (action === "state") {
        try {
          const payload = JSON.parse(text) as { ok?: boolean; safeReasonCode?: string; observation?: { terminal?: boolean } };
          if (payload.ok === true && payload.observation?.terminal !== true) {
            stateReady = true;
            terminalReason = null;
          } else {
            stateReady = false;
          }
          if (payload.ok === false && payload.observation?.terminal === true && typeof payload.safeReasonCode === "string") {
            terminalReason = payload.safeReasonCode;
          }
        } catch {
          stateReady = false;
          terminalReason = "liepin_opencli_malformed_state";
        }
      }
      resolve(text);
    });
    child.stdin.end(JSON.stringify(payload));
  });
}

export default function registerSeekTalentOpenCliBrowser(pi: ExtensionAPI) {
  pi.registerTool({
    name: "seektalent_opencli_status",
    label: "SeekTalent browser status",
    description: "Check whether the local OpenCLI browser channel is ready.",
    parameters: Type.Object({}),
    async execute(_toolCallId, _params) {
      return textResult(await runAction("status", {}));
    },
  });

  pi.registerTool({
    name: "seektalent_opencli_capabilities",
    label: "SeekTalent browser capabilities",
    description: "Return the restricted OpenCLI browser capability manifest without touching the provider page.",
    parameters: Type.Object({}),
    async execute(_toolCallId, _params) {
      return textResult(JSON.stringify({
        ok: true,
        action: "capabilities",
        safeReasonCode: "configured",
        counts: {},
        manifest: {
          backend: "opencli",
          tools: [
            "seektalent_opencli_status",
            "seektalent_opencli_capabilities",
            "seektalent_opencli_open_liepin_tab",
            "seektalent_opencli_state",
            "seektalent_opencli_get_url",
            "seektalent_opencli_find",
            "seektalent_opencli_fill",
            "seektalent_opencli_click",
            "seektalent_opencli_scroll",
            "seektalent_opencli_wait_time"
          ],
          forbidden: ["eval", "network", "upload", "download", "cookies", "storage"],
          sourcePolicies: ["liepin"]
        }
      }));
    },
  });

  pi.registerTool({
    name: "seektalent_opencli_open_liepin_tab",
    label: "Open Liepin search page",
    description: "Open a source-policy allowlisted Liepin search URL in a SeekTalent-owned tab for the configured OpenCLI session.",
    parameters: Type.Object({ url: Type.String() }),
    async execute(_toolCallId, params) {
      return textResult(await runAction("open_liepin_tab", params));
    },
  });

  pi.registerTool({
    name: "seektalent_opencli_state",
    label: "Read browser state",
    description: "Read the current page state through the restricted OpenCLI browser channel.",
    parameters: Type.Object({}),
    async execute(_toolCallId, _params) {
      return textResult(await runAction("state", {}));
    },
  });

  pi.registerTool({
    name: "seektalent_opencli_get_url",
    label: "Read current URL",
    description: "Read the current browser URL through the restricted OpenCLI browser channel.",
    parameters: Type.Object({}),
    async execute(_toolCallId, _params) {
      return textResult(await runAction("get_url", {}));
    },
  });

  pi.registerTool({
    name: "seektalent_opencli_find",
    label: "Find visible text",
    description: "Find a short visible text query in the current page state through the restricted OpenCLI browser channel.",
    parameters: Type.Object({ query: Type.String() }),
    async execute(_toolCallId, params) {
      return textResult(await runAction("find", params));
    },
  });

  pi.registerTool({
    name: "seektalent_opencli_fill",
    label: "Fill short keyword text",
    description: "Fill a page target with a short generated search keyword. Do not pass JD, notes, raw resumes, secrets, or provider payloads.",
    parameters: Type.Object({ target: Type.String(), text: Type.String() }),
    async execute(_toolCallId, params) {
      return textResult(await runAction("fill", params));
    },
  });

  pi.registerTool({
    name: "seektalent_opencli_click",
    label: "Click page target",
    description: "Click a target from the latest OpenCLI browser state.",
    parameters: Type.Object({ target: Type.String() }),
    async execute(_toolCallId, params) {
      return textResult(await runAction("click", params));
    },
  });

  pi.registerTool({
    name: "seektalent_opencli_scroll",
    label: "Scroll page",
    description: "Scroll the page up or down through the restricted OpenCLI browser channel.",
    parameters: Type.Object({ direction: Type.Union([Type.Literal("up"), Type.Literal("down")]) }),
    async execute(_toolCallId, params) {
      return textResult(await runAction("scroll", params));
    },
  });

  pi.registerTool({
    name: "seektalent_opencli_wait_time",
    label: "Wait briefly",
    description: "Wait a bounded number of seconds before the next read/action step.",
    parameters: Type.Object({ seconds: Type.Integer({ minimum: 1, maximum: 10 }) }),
    async execute(_toolCallId, params) {
      return textResult(await runAction("wait_time", params));
    },
  });
}
```

- [ ] **Step 4: Re-run extension test**

Run:

```bash
uv run pytest tests/test_pi_external_agent.py::test_opencli_pi_extension_exposes_only_restricted_tools -q
```

Expected: pass.

- [ ] **Step 5: Build-check the extension**

Run:

```bash
cd apps/web-svelte && bun build ../../src/seektalent/providers/pi_agent/pi_extensions/seektalent_opencli_browser.ts --outfile /tmp/seektalent-opencli-extension.js
```

Expected: pass. This verifies the TypeScript extension imports and Pi-facing registration code compile instead of relying only on text grep.

Also type-check the extension against Pi's real `ExtensionAPI` / `AgentToolResult` signatures. Add this command to the task-local verification:

```bash
cd apps/web-svelte && bunx tsc --noEmit --target ES2022 --module ESNext --moduleResolution bundler --strict --skipLibCheck ../../src/seektalent/providers/pi_agent/pi_extensions/seektalent_opencli_browser.ts
```

Expected: pass. This catches missing required `details` fields and wrong tool `execute(...)` signatures that `bun build` may not type-check.

## Task 5: Wire Settings, Pi Command, And Readiness

**Files:**
- Modify: `src/seektalent/config.py`
- Modify: `src/seektalent/providers/pi_agent/local_setup.py`
- Modify: `src/seektalent/dev_mode.py`
- Modify: `scripts/start-dev-workbench.sh`
- Test: `tests/test_liepin_config.py`
- Test: `tests/test_dev_mode_readiness.py`

- [ ] **Step 1: Add command-shape tests**

Add to `tests/test_liepin_config.py`:

```python
def test_opencli_backend_requires_opencli_extension_in_pi_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    skill = tmp_path / "liepin_search_cards.md"
    skill.write_text("skill", encoding="utf-8")
    provider_extension = tmp_path / "src/seektalent/providers/pi_agent/pi_extensions/bailian_deepseek.ts"
    provider_extension.parent.mkdir(parents=True)
    provider_extension.write_text("provider", encoding="utf-8")
    opencli_extension = tmp_path / "src/seektalent/providers/pi_agent/pi_extensions/seektalent_opencli_browser.ts"
    opencli_extension.write_text("opencli", encoding="utf-8")
    monkeypatch.setenv("SEEKTALENT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("SEEKTALENT_LIEPIN_WORKER_MODE", "pi_agent")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_ACCOUNT_BINDING_SECRET", "account-secret")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND", "opencli")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_PI_SKILL_PATH", str(skill))
    monkeypatch.setenv(
        "SEEKTALENT_LIEPIN_PI_COMMAND",
        f"pi --mode rpc --no-session --extension {provider_extension} --extension {opencli_extension}",
    )

    settings = AppSettings()

    assert str(opencli_extension) in settings.liepin_pi_command_argv


def test_opencli_backend_rejects_missing_opencli_extension(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    skill = tmp_path / "liepin_search_cards.md"
    skill.write_text("skill", encoding="utf-8")
    provider_extension = tmp_path / "src/seektalent/providers/pi_agent/pi_extensions/bailian_deepseek.ts"
    provider_extension.parent.mkdir(parents=True)
    provider_extension.write_text("provider", encoding="utf-8")
    monkeypatch.setenv("SEEKTALENT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("SEEKTALENT_LIEPIN_WORKER_MODE", "pi_agent")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_ACCOUNT_BINDING_SECRET", "account-secret")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND", "opencli")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_PI_SKILL_PATH", str(skill))
    monkeypatch.setenv("SEEKTALENT_LIEPIN_PI_COMMAND", f"pi --mode rpc --no-session --extension {provider_extension}")

    with pytest.raises(ValueError, match="required extension"):
        AppSettings()
```

Ensure these imports exist in `tests/test_liepin_config.py`:

```python
from pathlib import Path
```

- [ ] **Step 2: Add readiness tests**

Add to `tests/test_dev_mode_readiness.py`:

```python
def test_dev_mode_reports_opencli_extension_disconnected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env = {
        "SEEKTALENT_LIEPIN_WORKER_MODE": "pi_agent",
        "SEEKTALENT_LIEPIN_ACCOUNT_BINDING_SECRET": "account-secret",
        "SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND": "opencli",
        "SEEKTALENT_LIEPIN_OPENCLI_COMMAND": str(tmp_path / "node_modules/.bin/opencli"),
        "SEEKTALENT_LIEPIN_PI_SKILL_PATH": "src/seektalent/providers/pi_agent/pi_skills/liepin_search_cards.md",
    }

    status = build_dev_mode_env_diagnostics(env, workspace_root=tmp_path)
    components = {component.name: component for component in status.components}

    assert components["liepin_opencli_browser"].reasonCode in {
        "liepin_opencli_command_missing",
        "liepin_opencli_extension_disconnected",
    }


def test_opencli_local_setup_does_not_require_dokobot_mcp(tmp_path: Path) -> None:
    opencli = tmp_path / "apps/web-svelte/node_modules/.bin/opencli"
    opencli.parent.mkdir(parents=True)
    opencli.write_text("#!/bin/sh\n", encoding="utf-8")
    opencli.chmod(0o755)
    skill = tmp_path / "src/seektalent/providers/pi_agent/pi_skills/liepin_search_cards.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("skill", encoding="utf-8")
    provider_extension = tmp_path / "src/seektalent/providers/pi_agent/pi_extensions/bailian_deepseek.ts"
    provider_extension.parent.mkdir(parents=True)
    provider_extension.write_text("provider", encoding="utf-8")
    opencli_extension = tmp_path / "src/seektalent/providers/pi_agent/pi_extensions/seektalent_opencli_browser.ts"
    opencli_extension.write_text("opencli", encoding="utf-8")
    env = {
        "SEEKTALENT_LIEPIN_WORKER_MODE": "pi_agent",
        "SEEKTALENT_LIEPIN_ACCOUNT_BINDING_SECRET": "account-secret",
        "SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND": "opencli",
        "SEEKTALENT_LIEPIN_OPENCLI_COMMAND": "apps/web-svelte/node_modules/.bin/opencli",
        "SEEKTALENT_LIEPIN_PI_COMMAND": (
            f"pi --mode rpc --no-session --extension {provider_extension} --extension {opencli_extension}"
        ),
        "SEEKTALENT_LIEPIN_PI_SKILL_PATH": str(skill),
    }

    status = build_pi_agent_local_setup_status(env, workspace_root=tmp_path, which=lambda _: str(tmp_path / "pi"))

    assert status.components["opencli_browser"].status == "configured"
    assert status.components["dokobot_mcp"].status == "disabled"
    assert status.overall_status == "configured"
```

Use the existing import already present at the top of `tests/test_dev_mode_readiness.py`:

```python
from seektalent.dev_mode import build_dev_mode_env_diagnostics, build_dev_mode_status
from seektalent.providers.pi_agent.local_setup import build_pi_agent_local_setup_status
```

- [ ] **Step 3: Run tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_liepin_config.py::test_opencli_backend_requires_opencli_extension_in_pi_command tests/test_liepin_config.py::test_opencli_backend_rejects_missing_opencli_extension tests/test_dev_mode_readiness.py::test_dev_mode_reports_opencli_extension_disconnected tests/test_dev_mode_readiness.py::test_opencli_local_setup_does_not_require_dokobot_mcp -q
```

Expected: fail because OpenCLI command/readiness logic is not wired.

- [ ] **Step 4: Wire required extension marker**

In `src/seektalent/config.py`, update `liepin_pi_command_argv` so required extensions depend on backend:

```python
required_extension_markers: tuple[str, ...]
if self.liepin_worker_mode == "pi_agent" and self.liepin_browser_action_backend == "opencli":
    required_extension_markers = (
        "pi_extensions/bailian_deepseek.ts",
        "pi_extensions/seektalent_opencli_browser.ts",
    )
elif self.liepin_worker_mode == "pi_agent":
    required_extension_markers = (
        "pi_extensions/bailian_deepseek.ts",
        "pi-mcp-adapter/index.ts",
    )
else:
    required_extension_markers = ()
```

- [ ] **Step 5: Add static local setup component**

In `src/seektalent/providers/pi_agent/local_setup.py`, branch setup components by `SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND`. OpenCLI mode must not require DokoBot MCP config or `pi-mcp-adapter/index.ts`.

Update the component assembly:

```python
browser_backend = _env_value(env, "SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND") or "disabled"
components = {
    "worker_mode": PiAgentLocalSetupComponent("configured", "configured"),
    "account_binding_secret": _account_secret_component(env),
    "pi_command": _pi_command_component(env, workspace_root=workspace, which=which, browser_backend=browser_backend),
    "pi_skill": _pi_skill_component(env, workspace_root=workspace),
}
if browser_backend == "opencli":
    components["opencli_browser"] = _opencli_component(env, workspace_root=workspace, which=which)
    components["dokobot_mcp"] = PiAgentLocalSetupComponent("disabled", "liepin_pi_disabled")
else:
    dokobot_tool_name = _env_value(env, "SEEKTALENT_LIEPIN_PI_DOKOBOT_TOOL_NAME") or DEFAULT_DOKOBOT_TOOL_NAME
    components["opencli_browser"] = PiAgentLocalSetupComponent("disabled", "liepin_opencli_backend_disabled")
    components["dokobot_mcp"] = _dokobot_mcp_component(env, workspace_root=workspace, dokobot_tool_name=dokobot_tool_name)
```

Change `_pi_command_component(...)` to accept `browser_backend: str` and choose the required extension by backend:

```python
def _pi_command_component(
    env: Mapping[str, str | None],
    *,
    workspace_root: Path,
    which: Callable[[str], str | None],
    browser_backend: str,
) -> PiAgentLocalSetupComponent:
    command = _env_value(env, "SEEKTALENT_LIEPIN_PI_COMMAND") or DEFAULT_LIEPIN_PI_COMMAND
    try:
        argv = shlex.split(command)
    except ValueError:
        return PiAgentLocalSetupComponent("invalid", "liepin_pi_command_invalid")
    if not argv or _arg_value(argv, "--mode") != "rpc" or "--no-session" not in argv or "--skill" in argv:
        return PiAgentLocalSetupComponent("invalid", "liepin_pi_command_invalid")
    extensions = _extension_values(argv)
    if not any("pi_extensions/bailian_deepseek.ts" in extension for extension in extensions):
        return PiAgentLocalSetupComponent("invalid", "liepin_pi_command_invalid")
    if browser_backend == "opencli":
        required_extension = _extension_matching(extensions, "pi_extensions/seektalent_opencli_browser.ts")
        missing_reason = "liepin_opencli_extension_disconnected"
    else:
        required_extension = _extension_matching(extensions, "pi-mcp-adapter/index.ts")
        missing_reason = "liepin_pi_mcp_adapter_missing"
    if required_extension is None:
        return PiAgentLocalSetupComponent("needs_setup", missing_reason)
    executable = argv[0]
    if not _executable_resolves(executable, which=which):
        return PiAgentLocalSetupComponent("needs_setup", "liepin_pi_command_missing")
    if not _extension_file_exists(required_extension, workspace_root=workspace_root):
        return PiAgentLocalSetupComponent("needs_setup", missing_reason)
    return PiAgentLocalSetupComponent("configured", "configured")
```

Implement:

```python
def _opencli_component(env: Mapping[str, str | None], *, workspace_root: Path, which: Callable[[str], str | None]) -> PiAgentLocalSetupComponent:
    backend = _env_value(env, "SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND") or "disabled"
    if backend != "opencli":
        return PiAgentLocalSetupComponent("disabled", "liepin_opencli_backend_disabled")
    command = _env_value(env, "SEEKTALENT_LIEPIN_OPENCLI_COMMAND") or "apps/web-svelte/node_modules/.bin/opencli"
    argv = shlex.split(command)
    if not argv:
        return PiAgentLocalSetupComponent("needs_setup", "liepin_opencli_command_missing")
    executable = argv[0]
    if not _executable_resolves(executable, which=which):
        path = _resolve_optional_path(executable, workspace_root=workspace_root)
        if path is None or not path.exists():
            return PiAgentLocalSetupComponent("needs_setup", "liepin_opencli_command_missing")
    return PiAgentLocalSetupComponent("configured", "configured")
```

Surface it from `dev_mode.py` as the public component name `"liepin_opencli_browser"`. Update `_pi_mcp_components_from_env(...)` so OpenCLI mode maps `status.components["opencli_browser"]` to the browser-channel diagnostic and does not render DokoBot MCP diagnostics:

```python
backend = _env_value(env, "SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND") or "disabled"
if backend == "opencli":
    component = status.components["opencli_browser"]
    return [
        _component(
            "liepin_opencli_browser",
            "Browser channel",
            _dev_status_from_pi_setup(component, fallback="missing"),
            reason_code=_dev_reason_from_pi_setup(component),
        )
    ]
return _pi_mcp_components_from_reason(status.components["dokobot_mcp"].reason_code)
```

- [ ] **Step 6: Update dev launcher**

In `scripts/start-dev-workbench.sh`, when OpenCLI mode is enabled:

```bash
if [ "${SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND:-disabled}" = "opencli" ]; then
  if [ ! -x "apps/web-svelte/node_modules/.bin/opencli" ]; then
    echo "OpenCLI CLI dependency is missing; running frontend dependency install." >&2
    (cd apps/web-svelte && bun install)
  fi
fi
```

Do not exit if OpenCLI is still missing after install. Backend readiness will block only Liepin.

- [ ] **Step 7: Re-run focused tests**

Run:

```bash
uv run pytest tests/test_liepin_config.py::test_opencli_backend_requires_opencli_extension_in_pi_command tests/test_liepin_config.py::test_opencli_backend_rejects_missing_opencli_extension tests/test_dev_mode_readiness.py::test_dev_mode_reports_opencli_extension_disconnected tests/test_dev_mode_readiness.py::test_opencli_local_setup_does_not_require_dokobot_mcp -q
```

Expected: pass.

## Task 6: Update Liepin Pi Capability And Skill Contract

**Files:**
- Modify: `src/seektalent/providers/liepin/pi_executor.py`
- Modify: `src/seektalent/providers/liepin/pi_worker_client.py`
- Modify: `src/seektalent/providers/liepin/client.py`
- Modify: `src/seektalent/providers/pi_agent/pi_skills/liepin_search_cards.md`
- Test: `tests/test_liepin_pi_executor.py`
- Test: `tests/test_liepin_pi_worker_client.py`

- [ ] **Step 1: Add executor capability tests**

Add to `tests/test_liepin_pi_executor.py`:

```python
def test_capability_probe_accepts_opencli_status_and_declared_manifest_without_action_side_effects() -> None:
    executor = _capability_executor(
        envelope={
            "schema_version": "seektalent.pi_capability_probe.v1",
            "status": "ready",
            "read_tool_name": "seektalent_opencli_capabilities",
            "action_tool_names": [
                "seektalent_opencli_status",
                "seektalent_opencli_capabilities",
                "seektalent_opencli_open_liepin_tab",
                "seektalent_opencli_state",
                "seektalent_opencli_fill",
                "seektalent_opencli_click",
            ],
            "proof_kind": "trusted_manifest_and_observed_tool_event",
            "capability_manifest_ref": "artifact://protected/capability/manifest.json",
            "tool_evidence_ref": "artifact://protected/capability/tools.json",
            "allowed_hosts": ["www.liepin.com"],
        },
        observed_tool_names=(
            "seektalent_opencli_status",
            "seektalent_opencli_capabilities",
        ),
    )

    result = executor.probe_capabilities(
        expected_dokobot_tool_name="dokobot",
        expected_observed_tool_names=(),
        expected_opencli_observed_tool_names=("seektalent_opencli_status", "seektalent_opencli_capabilities"),
        expected_opencli_declared_tool_names=(
            "seektalent_opencli_status",
            "seektalent_opencli_capabilities",
            "seektalent_opencli_open_liepin_tab",
            "seektalent_opencli_state",
            "seektalent_opencli_fill",
            "seektalent_opencli_click",
        ),
    )

    assert result.ready is True


def test_capability_probe_blocks_when_opencli_tool_unobserved() -> None:
    executor = _capability_executor(
        envelope={
            "schema_version": "seektalent.pi_capability_probe.v1",
            "status": "ready",
            "read_tool_name": "seektalent_opencli_capabilities",
            "action_tool_names": ["seektalent_opencli_status", "seektalent_opencli_capabilities"],
            "proof_kind": "trusted_manifest_and_observed_tool_event",
            "capability_manifest_ref": "artifact://protected/capability/manifest.json",
            "tool_evidence_ref": "artifact://protected/capability/tools.json",
            "allowed_hosts": ["www.liepin.com"],
        },
        observed_tool_names=("seektalent_opencli_status",),
    )

    result = executor.probe_capabilities(
        expected_dokobot_tool_name="dokobot",
        expected_observed_tool_names=(),
        expected_opencli_observed_tool_names=("seektalent_opencli_status", "seektalent_opencli_capabilities"),
        expected_opencli_declared_tool_names=("seektalent_opencli_status", "seektalent_opencli_capabilities"),
    )

    assert result.ready is False
    assert result.safe_reason_code == "liepin_opencli_status_unavailable"
```

Use the existing `_capability_executor(...)` helper in `tests/test_liepin_pi_executor.py`.

- [ ] **Step 2: Add worker client tests**

Add to `tests/test_liepin_pi_worker_client.py`:

```python
def test_pi_worker_client_passes_opencli_expected_tools_to_capability_probe() -> None:
    executor = FakeExecutor()
    client = LiepinPiWorkerClient(
        executor,
        session_id="session",
        connection_id="connection",
        provider_account_lock_key="lock",
        dokobot_tool_name="dokobot",
        expected_observed_tool_names=(),
        expected_opencli_observed_tool_names=("seektalent_opencli_status", "seektalent_opencli_capabilities"),
        expected_opencli_declared_tool_names=(
            "seektalent_opencli_status",
            "seektalent_opencli_capabilities",
            "seektalent_opencli_open_liepin_tab",
            "seektalent_opencli_state",
            "seektalent_opencli_fill",
            "seektalent_opencli_click",
        ),
    )

    asyncio.run(client.ensure_ready())

    assert executor.capability_calls[-1]["expected_opencli_observed_tool_names"] == (
        "seektalent_opencli_status",
        "seektalent_opencli_capabilities",
    )
```

- [ ] **Step 3: Run tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_liepin_pi_executor.py::test_capability_probe_accepts_opencli_status_and_declared_manifest_without_action_side_effects tests/test_liepin_pi_executor.py::test_capability_probe_blocks_when_opencli_tool_unobserved tests/test_liepin_pi_worker_client.py::test_pi_worker_client_passes_opencli_expected_tools_to_capability_probe -q
```

Expected: fail because executor/client signatures do not include OpenCLI expectations.

- [ ] **Step 4: Update executor signature**

In `src/seektalent/providers/liepin/pi_executor.py`, change:

```python
def probe_capabilities(
    self,
    *,
    expected_dokobot_tool_name: str,
    expected_observed_tool_names: Sequence[str] = (),
) -> PiLiepinCapabilityProbeResult:
```

to:

```python
def probe_capabilities(
    self,
    *,
    expected_dokobot_tool_name: str,
    expected_observed_tool_names: Sequence[str] = (),
    expected_opencli_observed_tool_names: Sequence[str] = (),
    expected_opencli_declared_tool_names: Sequence[str] = (),
) -> PiLiepinCapabilityProbeResult:
```

After parsing the capability envelope and observed tool names, add:

```python
if expected_opencli_observed_tool_names or expected_opencli_declared_tool_names:
    declared = {envelope.read_tool_name, *envelope.action_tool_names}
    required_declared = set(expected_opencli_declared_tool_names)
    if not required_declared.issubset(declared):
        return PiLiepinCapabilityProbeResult(ready=False, safe_reason_code="liepin_opencli_status_unavailable")
    observed = set(task_result.observed_tool_names)
    required_observed = set(expected_opencli_observed_tool_names)
    if not required_observed.issubset(observed):
        return PiLiepinCapabilityProbeResult(ready=False, safe_reason_code="liepin_opencli_status_unavailable")
    return PiLiepinCapabilityProbeResult(ready=True)
```

Do this before DokoBot-specific required-tool validation so OpenCLI mode does not require DokoBot.

- [ ] **Step 5: Update worker client signature**

In `src/seektalent/providers/liepin/pi_worker_client.py`, add constructor field:

```python
expected_opencli_observed_tool_names: tuple[str, ...] = (),
expected_opencli_declared_tool_names: tuple[str, ...] = (),
```

Store it:

```python
self._expected_opencli_observed_tool_names = expected_opencli_observed_tool_names
self._expected_opencli_declared_tool_names = expected_opencli_declared_tool_names
```

Pass it in `ensure_ready()`:

```python
expected_opencli_observed_tool_names=self._expected_opencli_observed_tool_names,
expected_opencli_declared_tool_names=self._expected_opencli_declared_tool_names,
```

- [ ] **Step 6: Update client factory**

In `src/seektalent/providers/liepin/client.py`, when constructing `LiepinPiWorkerClient`, pass:

```python
expected_opencli_observed_tool_names=(
    ("seektalent_opencli_status", "seektalent_opencli_capabilities")
    if settings.liepin_browser_action_backend == "opencli"
    else ()
),
expected_opencli_declared_tool_names=(
    (
        "seektalent_opencli_status",
        "seektalent_opencli_capabilities",
        "seektalent_opencli_open_liepin_tab",
        "seektalent_opencli_state",
        "seektalent_opencli_fill",
        "seektalent_opencli_click",
    )
    if settings.liepin_browser_action_backend == "opencli"
    else ()
),
```

Keep existing DokoBot settings for non-OpenCLI modes.

- [ ] **Step 7: Pass OpenCLI runtime env into Pi**

In `src/seektalent/providers/liepin/client.py`, import `sys` and `shlex`, and add these values to the `PiRpcAgentClient(..., env={...})` dict when `settings.liepin_browser_action_backend == "opencli"`:

```python
opencli_env = {}
if settings.liepin_browser_action_backend == "opencli":
    opencli_env = {
        "SEEKTALENT_PYTHON": sys.executable,
        "PYTHONPATH": str(settings.project_root / "src"),
        "SEEKTALENT_WORKSPACE_ROOT": str(settings.project_root),
        "SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND": "opencli",
        "SEEKTALENT_LIEPIN_OPENCLI_COMMAND": shlex.join(settings.liepin_opencli_command_argv),
        "SEEKTALENT_LIEPIN_OPENCLI_SESSION": settings.liepin_opencli_session,
        "SEEKTALENT_LIEPIN_OPENCLI_ALLOWED_HOSTS_JSON": json.dumps(list(settings.liepin_opencli_allowed_hosts)),
        "SEEKTALENT_LIEPIN_OPENCLI_ALLOWED_START_URLS_JSON": json.dumps(list(settings.liepin_opencli_allowed_start_urls)),
        "SEEKTALENT_LIEPIN_OPENCLI_MAX_ACTIONS_PER_TASK": str(settings.liepin_opencli_max_actions_per_task),
        "SEEKTALENT_LIEPIN_OPENCLI_MAX_PAGES_PER_TASK": str(settings.liepin_opencli_max_pages_per_task),
        "SEEKTALENT_LIEPIN_OPENCLI_MAX_CARDS_PER_TASK": str(settings.liepin_opencli_max_cards_per_task),
        "SEEKTALENT_LIEPIN_OPENCLI_TIMEOUT_SECONDS": str(settings.liepin_opencli_timeout_seconds),
    }
```

Then merge it into the existing Pi env:

```python
env={
    "SEEKTALENT_PI_BAILIAN_API_KEY": resolve_text_llm_api_key(settings) or "",
    "SEEKTALENT_PI_BAILIAN_BASE_URL": resolve_text_llm_base_url(settings),
    "SEEKTALENT_PI_BAILIAN_MODEL_ID": settings.liepin_pi_model_id or settings.workbench_note_writer_model_id,
    **opencli_env,
},
browser_backend_description=(
    "SeekTalent OpenCLI browser tools: seektalent_opencli_status, seektalent_opencli_capabilities"
    if settings.liepin_browser_action_backend == "opencli"
    else None
),
```

Do not put API keys, account binding secrets, cookies, storage, or raw page text in command argv.

- [ ] **Step 8: Update Liepin skill**

In `src/seektalent/providers/pi_agent/pi_skills/liepin_search_cards.md`, add a section:

```markdown
## OpenCLI Browser Mode

When SeekTalent OpenCLI tools are available, use them for both page reading and page action.

Allowed tools:
- `seektalent_opencli_status`
- `seektalent_opencli_capabilities`
- `seektalent_opencli_open_liepin_tab`
- `seektalent_opencli_state`
- `seektalent_opencli_get_url`
- `seektalent_opencli_find`
- `seektalent_opencli_fill`
- `seektalent_opencli_click`
- `seektalent_opencli_scroll`
- `seektalent_opencli_wait_time`

Use only short generated search keywords in `seektalent_opencli_fill`.
Never pass the full JD, notes, raw resumes, credentials, cookies, storage, or provider payloads to browser tools.
Do not use OpenCLI site adapters. Do not use eval, network, upload, download, cookies, storage, contact, chat, payment, or account settings.
Stop and return a blocked safe envelope on login-required, identity intercept, captcha, risk page, unknown modal, contact prompt, chat prompt, payment prompt, download prompt, or detail-open requirement.
```

- [ ] **Step 9: Re-run focused tests**

Run:

```bash
uv run pytest tests/test_liepin_pi_executor.py::test_capability_probe_accepts_opencli_status_and_declared_manifest_without_action_side_effects tests/test_liepin_pi_executor.py::test_capability_probe_blocks_when_opencli_tool_unobserved tests/test_liepin_pi_worker_client.py::test_pi_worker_client_passes_opencli_expected_tools_to_capability_probe -q
```

Expected: pass.

## Task 7: Wire Safe Reason Projection And UI Copy

**Files:**
- Modify: `src/seektalent_ui/workbench_routes.py`
- Modify: `apps/web-svelte/src/lib/workbench/sourceDisplay.ts`
- Test: `tests/test_workbench_api.py` or `tests/test_workbench_semantic_guardrails.py`
- Test: `apps/web-svelte/src/lib/workbench/sourceDisplay.test.ts`

- [ ] **Step 1: Add backend reason projection test**

In an existing Workbench route/source-state test file such as `tests/test_workbench_api.py` or `tests/test_workbench_semantic_guardrails.py`, add:

```python
def test_runtime_source_state_preserves_opencli_reason_code() -> None:
    reason = "liepin_opencli_extension_disconnected"

    assert reason in RUNTIME_SOURCE_REASON_CODES


def test_liepin_start_probe_preserves_opencli_reason_code() -> None:
    reason = _liepin_start_probe_error_reason(
        LiepinWorkerModeError("opencli extension disconnected", code="liepin_opencli_extension_disconnected")
    )

    assert reason == "liepin_opencli_extension_disconnected"


def test_liepin_dev_mode_setup_reason_preserves_opencli_reason_code() -> None:
    request = _request_with_dev_mode_component(reason_code="liepin_opencli_command_missing")

    assert _liepin_dev_mode_setup_reason(request) == "liepin_opencli_command_missing"
```

Use the existing import paths and local request/test helpers in that file. If there is no request helper, create the smallest app-state fixture needed to attach `dev_mode_env_diagnostics.components`.

- [ ] **Step 2: Add Svelte copy test**

In `apps/web-svelte/src/lib/workbench/sourceDisplay.test.ts`, add:

```ts
it("maps OpenCLI reason codes to generic browser-channel copy", () => {
  expect(sourceReasonLabel("liepin_opencli_extension_disconnected")).toContain("浏览器");
  expect(sourceReasonLabel("liepin_opencli_login_required")).toContain("登录猎聘");
  expect(sourceReasonLabel("liepin_opencli_identity_intercept")).toContain("招聘身份");
  expect(sourceReasonLabel("liepin_opencli_risk_page")).toContain("人工确认");
  expect(sourceReasonLabel("liepin_opencli_host_blocked")).toContain("可检索范围");
  expect(sourceReasonLabel("liepin_opencli_extension_disconnected")).not.toContain("OpenCLI");
  expect(sourceReasonLabel("liepin_opencli_extension_disconnected")).not.toContain("CDP");
  expect(sourceReasonLabel("liepin_opencli_extension_disconnected")).not.toContain("MCP");
  expect(sourceReasonLabel("liepin_opencli_extension_disconnected")).not.toContain("DokoBot");
  expect(sourceReasonLabel("liepin_opencli_extension_disconnected")).not.toContain("风控");
});
```

- [ ] **Step 3: Run tests and confirm they fail**

Run:

```bash
uv run pytest tests/test_workbench_api.py::test_runtime_source_state_preserves_opencli_reason_code -q
cd apps/web-svelte && bun run test -- sourceDisplay.test.ts
```

Expected: fail because reason codes/copy are missing.

- [ ] **Step 4: Add reason codes**

In `src/seektalent_ui/workbench_routes.py`, add to `RUNTIME_SOURCE_REASON_CODES`:

```python
"liepin_opencli_backend_disabled",
"liepin_opencli_command_missing",
"liepin_opencli_extension_disconnected",
"liepin_opencli_status_unavailable",
"liepin_opencli_forbidden_command",
"liepin_opencli_forbidden_text",
"liepin_opencli_host_blocked",
"liepin_opencli_start_url_blocked",
"liepin_opencli_window_policy_blocked",
"liepin_opencli_budget_exhausted",
"liepin_opencli_timeout",
"liepin_opencli_login_required",
"liepin_opencli_identity_intercept",
"liepin_opencli_risk_page",
"liepin_opencli_unknown_modal",
"liepin_opencli_source_policy_missing",
"liepin_opencli_malformed_state",
```

- [ ] **Step 5: Preserve OpenCLI codes in route helpers**

Update `_liepin_start_probe_error_reason(...)` so it preserves allowlisted `liepin_opencli_*` codes in addition to the existing `liepin_pi_*` and `liepin_browser_*` codes:

```python
if code in RUNTIME_SOURCE_REASON_CODES and (
    code.startswith("liepin_pi_")
    or code.startswith("liepin_browser_")
    or code.startswith("liepin_opencli_")
):
    return code
```

Update `_liepin_dev_mode_setup_reason(...)` so OpenCLI static/browser setup diagnostics can become source-run reason codes:

```python
if (
    isinstance(code, str)
    and code in RUNTIME_SOURCE_REASON_CODES
    and (
        code.startswith("liepin_pi_")
        or code.startswith("liepin_opencli_")
    )
    and code not in {"liepin_pi_disabled", "liepin_opencli_backend_disabled"}
):
    return code
```

This is required because the current helpers gate reason codes by prefix before the later runtime source-state projection sees them.

- [ ] **Step 6: Add UI copy mapping**

In `apps/web-svelte/src/lib/workbench/sourceDisplay.ts`, map `liepin_opencli_*` reasons to category-specific business language:

```ts
if (reasonCode === 'liepin_opencli_login_required') {
  return '请先在本机 Chrome 登录猎聘，然后重新启动检索。';
}
if (reasonCode === 'liepin_opencli_identity_intercept') {
  return '猎聘需要确认当前招聘身份，请在本机 Chrome 完成后重试。';
}
if (reasonCode === 'liepin_opencli_risk_page' || reasonCode === 'liepin_opencli_unknown_modal') {
  return '猎聘页面需要人工确认，请处理后重新启动检索。';
}
if (reasonCode === 'liepin_opencli_host_blocked' || reasonCode === 'liepin_opencli_start_url_blocked') {
  return '当前猎聘页面不在可检索范围，请回到猎聘搜索页后重试。';
}
if (reasonCode?.startsWith('liepin_opencli_')) {
  return '本机 Chrome 浏览器通道未就绪，请确认扩展已启用后重试。';
}
```

Do not include `OpenCLI`, `CDP`, `MCP`, `debugger`, `DokoBot`, or risk-control wording in main UI copy.

- [ ] **Step 7: Re-run tests**

Run:

```bash
uv run pytest tests/test_workbench_api.py::test_runtime_source_state_preserves_opencli_reason_code -q
cd apps/web-svelte && bun run test -- sourceDisplay.test.ts
```

Expected: pass.

## Task 8: Harden Boundary Tests

**Files:**
- Modify: `tests/test_pi_agent_boundaries.py`

- [ ] **Step 1: Add boundary tests**

Add to `tests/test_pi_agent_boundaries.py`:

```python
def test_runtime_and_workbench_do_not_call_opencli_directly() -> None:
    forbidden = (
        "OpenCliBrowserRunner(",
        "SubprocessOpenCliCommandRunner",
        "subprocess.run([\"opencli",
        "subprocess.run(['opencli",
        "Popen([\"opencli",
        "Popen(['opencli",
    )
    scanned_roots = [Path("src/seektalent/runtime"), Path("src/seektalent_ui")]
    findings: list[str] = []
    for root in scanned_roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for marker in forbidden:
                if marker in text:
                    findings.append(f"{path} contains {marker}")
    assert findings == []


def test_runtime_and_workbench_may_only_reference_opencli_safe_reason_codes() -> None:
    allowed_markers = ("liepin_opencli_",)
    scanned_roots = [Path("src/seektalent/runtime"), Path("src/seektalent_ui")]
    findings: list[str] = []
    for root in scanned_roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "opencli" in text.lower() and not any(marker in text for marker in allowed_markers):
                findings.append(str(path))
    assert findings == []


def test_opencli_helper_does_not_allow_high_risk_commands() -> None:
    text = Path("src/seektalent/providers/pi_agent/opencli_browser.py").read_text(encoding="utf-8")

    assert '"eval"' in text
    assert '"network"' in text
    assert '"upload"' in text
    assert "FORBIDDEN_BROWSER_COMMANDS" in text
    assert "document.cookie" in text
    assert "localstorage" in text.lower()
    assert "sessionstorage" in text.lower()
    assert "browser eval" not in text
```

- [ ] **Step 2: Run boundary tests**

Run:

```bash
uv run pytest tests/test_pi_agent_boundaries.py::test_runtime_and_workbench_do_not_call_opencli_directly tests/test_pi_agent_boundaries.py::test_opencli_helper_does_not_allow_high_risk_commands -q
```

Expected: pass after previous tasks.

## Task 9: Documentation And Manual Spike Instructions

**Files:**
- Modify: `README.md`
- Modify: `docs/configuration.md`
- Modify: `docs/development.md`

- [ ] **Step 1: Add docs text**

Add a developer-facing section:

```markdown
### Liepin OpenCLI Browser Spike

SeekTalent can run a Liepin card-search spike through Pi and a restricted OpenCLI browser backend.
The OpenCLI CLI package is installed with the Svelte workspace dependencies. The Chrome extension is installed and authorized by the user.

Enable:

```dotenv
SEEKTALENT_LIEPIN_WORKER_MODE=pi_agent
SEEKTALENT_LIEPIN_BROWSER_ACTION_BACKEND=opencli
SEEKTALENT_LIEPIN_OPENCLI_COMMAND=apps/web-svelte/node_modules/.bin/opencli
SEEKTALENT_LIEPIN_OPENCLI_SESSION=seektalent-liepin
```

Manual check:

```bash
bun install --cwd apps/web-svelte
apps/web-svelte/node_modules/.bin/opencli doctor
printf '{}' | uv run python -m seektalent.providers.pi_agent.opencli_browser_cli status
printf '{"url":"https://www.liepin.com/zhaopin/"}' | uv run python -m seektalent.providers.pi_agent.opencli_browser_cli open_liepin_tab
printf '{}' | uv run python -m seektalent.providers.pi_agent.opencli_browser_cli state
```

Safety limits:

- Use only the restricted SeekTalent OpenCLI tools inside Pi.
- Do not use OpenCLI site adapters for Liepin live card search.
- Do not use eval, network capture, cookies, storage, uploads, downloads, contact, chat, payment, account settings, or provider API replay.
- Stop on login, identity intercept, captcha, risk page, unknown modal, contact prompt, chat prompt, payment prompt, or download prompt.

Packaging note:

- Source/dev workspace launchers install OpenCLI through `apps/web-svelte` dependencies.
- Python-only/PyPI installation does not automatically include Node dependencies yet. In those installs OpenCLI mode must remain blocked with `liepin_opencli_command_missing` unless a packaged installer or first-run dependency bootstrap is added.
```

- [ ] **Step 2: Run docs grep**

Run:

```bash
rg -n "cliclick|CGEvent|pynput|system-level keyboard" README.md docs/configuration.md docs/development.md
```

Expected: no new matches in the edited OpenCLI documentation sections.

## Task 10: Final Verification

**Files:**
- All files touched by previous tasks.

- [ ] **Step 1: Run Python tests**

Run:

```bash
uv run pytest tests/test_liepin_config.py tests/test_pi_opencli_browser.py tests/test_liepin_pi_executor.py tests/test_liepin_pi_worker_client.py tests/test_liepin_runtime_source_lane.py tests/test_runtime_source_lanes.py tests/test_dev_mode_readiness.py tests/test_pi_external_agent.py tests/test_pi_agent_boundaries.py tests/test_workbench_api.py tests/test_workbench_semantic_guardrails.py -q
```

Expected: pass.

- [ ] **Step 2: Run Ruff**

Run:

```bash
uv run ruff check src/seektalent/config.py src/seektalent/runtime/source_lanes.py src/seektalent/providers/pi_agent src/seektalent/providers/liepin src/seektalent_ui/workbench_routes.py tests/test_liepin_config.py tests/test_pi_opencli_browser.py tests/test_liepin_pi_executor.py tests/test_liepin_pi_worker_client.py tests/test_liepin_runtime_source_lane.py tests/test_runtime_source_lanes.py tests/test_dev_mode_readiness.py tests/test_pi_external_agent.py tests/test_pi_agent_boundaries.py tests/test_workbench_api.py tests/test_workbench_semantic_guardrails.py
```

Expected: pass.

- [ ] **Step 3: Run Svelte verification**

Run:

```bash
cd apps/web-svelte && bun install --frozen-lockfile && bun run check && bun run test
```

Expected: pass.

- [ ] **Step 4: Build-check Pi OpenCLI extension**

Run:

```bash
cd apps/web-svelte && bun build ../../src/seektalent/providers/pi_agent/pi_extensions/seektalent_opencli_browser.ts --outfile /tmp/seektalent-opencli-extension.js
cd apps/web-svelte && bunx tsc --noEmit --target ES2022 --module ESNext --moduleResolution bundler --strict --skipLibCheck ../../src/seektalent/providers/pi_agent/pi_extensions/seektalent_opencli_browser.ts
```

Expected: pass.

- [ ] **Step 5: Run diff hygiene**

Run:

```bash
git diff --check docs/superpowers/specs/2026-05-20-pi-macos-action-backend-liepin-card-search-design.md docs/superpowers/plans/2026-05-20-pi-macos-action-backend-liepin-card-search.md src/seektalent/config.py src/seektalent/providers/pi_agent src/seektalent/providers/liepin src/seektalent_ui/workbench_routes.py apps/web-svelte/src/lib/workbench/sourceDisplay.ts tests
```

Expected: no output.

- [ ] **Step 6: Manual OpenCLI smoke when the extension is installed**

Run:

```bash
apps/web-svelte/node_modules/.bin/opencli doctor
printf '{}' | uv run python -m seektalent.providers.pi_agent.opencli_browser_cli status
printf '{"url":"https://www.liepin.com/zhaopin/"}' | uv run python -m seektalent.providers.pi_agent.opencli_browser_cli open_liepin_tab
printf '{}' | uv run python -m seektalent.providers.pi_agent.opencli_browser_cli state
```

Expected:

- doctor reports daemon and extension connected;
- the restricted helper reports the browser channel status;
- a Liepin tab opens through the helper;
- state returns a Liepin page through the helper.

Do not run this manual smoke against recruiter/private pages until the user explicitly confirms the correct page and identity state.

## Self-Review

Spec coverage:

- OpenCLI read/action backend: Tasks 1-6.
- CLI auto-install through project dependency: Task 1.
- Packaged/PyPI dependency boundary: Tasks 1 and 9.
- User-installed extension diagnosis: Tasks 5 and 9.
- Pi-only tool surface: Tasks 4, 6, 8.
- Pi-only observation versus public payload split: Tasks 2-4 and 8.
- No Runtime/Workbench direct OpenCLI: Task 8.
- Tab/session contract: Tasks 2, 4, 9, 10.
- Safe reason projection and UI copy: Task 7.
- DokoBot no longer required for this mode: Tasks 5, 6, and 9.
- Account-safety restrictions and forbidden commands: Tasks 2, 4, 8, 9.

Placeholder scan:

- No vague task remains.
- Every code-facing task names exact files, commands, and expected outcomes.

Type consistency:

- Settings names use `liepin_browser_action_backend` and `liepin_opencli_*`.
- Python helper types use `OpenCliBrowser*`.
- Pi tools use `seektalent_opencli_*`.
- Safe reason codes use `liepin_opencli_*`.
