# PI Agent Boundary Guards And Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce PI Agent browser-boundary rules and keep the legacy Liepin worker boundary aligned while DokoBot action mode remains capability-gated.

**Scope:** This plan implements only the boundary-guard and legacy compatibility slice of the shared spec. It does not implement provider connection safety, DokoBot action-manifest trust policy, local-only transport enforcement, detail grants, artifact access control, runner dispatch, concurrency leases, or UI exposure. Those are handled by the other linked plans.

**Architecture:** The PI Agent owns one canonical forbidden-operation registry in JSON. Liepin skill recipes, the Python AST scanner, and the Bun worker AST checker load or mirror that registry so forbidden-operation lists cannot silently drift. The scanners must reject executable misuse of direct authenticated API replay, DokoBot/DevTools network inspection, Playwright network interception, arbitrary in-page script evaluation, cookie/header/storage manipulation, CDP access, and raw HTTP clients inside provider automation code. The Bun worker checker must distinguish provider-action code from session lifecycle/bootstrap code: provider actions get the strict browser-operation rules, while login/session bootstrap code may use narrow `storageState` flows needed to establish a user-owned browser session. They must not flag the canonical registry declaration itself, comments, or inert fixture strings as executable violations.

**Tech Stack:** Python 3.12, Python `ast`, pytest, Bun, TypeScript compiler API, existing `apps/liepin-worker` boundary check.

**Spec:** `docs/superpowers/specs/2026-05-13-provider-interaction-agent-dokobot-design.md`

**Depends On:**
- `docs/superpowers/plans/2026-05-13-pi-agent-contracts-and-skill-recipes.md`
- `docs/superpowers/plans/2026-05-13-dokobot-capability-and-protected-artifacts.md`
- `docs/superpowers/plans/2026-05-13-detail-grants-and-backend-dispatch.md`

---

## File Structure

- Add: `src/seektalent/providers/pi_agent/boundary_registry.json`
  - Canonical cross-language forbidden-operation registry.
- Add: `src/seektalent/providers/pi_agent/boundary_patterns.py`
  - Small loader exposing registry-derived tuples for Python code and skill recipes.
- Modify: `src/seektalent/providers/liepin/pi_skills.py`
  - Import `FORBIDDEN_PROVIDER_OPERATIONS` instead of declaring duplicate strings.
- Add: `tools/check_pi_agent_boundaries.py`
  - AST-first Python scanner for provider automation code.
- Test: `tests/test_pi_agent_boundaries.py`
  - Registry, Python scanner, URL matcher, and current-source-root regression tests.
- Modify: `apps/liepin-worker/scripts/checkBoundaries.ts`
  - Keep the Bun checker AST-first and add missing registry-backed operation checks.
- Modify: `apps/liepin-worker/tests/boundaries.test.ts`
  - Add TS boundary coverage for network inspection, route interception, script evaluation, cookie/header/storage manipulation, CDP, and in-page network calls.

## Task 1: Add AST-First Boundary Scan And Compatibility Verification

**Files:**
- Create: `src/seektalent/providers/pi_agent/boundary_registry.json`
- Create: `src/seektalent/providers/pi_agent/boundary_patterns.py`
- Modify: `src/seektalent/providers/liepin/pi_skills.py`
- Create: `tools/check_pi_agent_boundaries.py`
- Test: `tests/test_pi_agent_boundaries.py`
- Modify: `apps/liepin-worker/scripts/checkBoundaries.ts`
- Modify: `apps/liepin-worker/tests/boundaries.test.ts`

- [ ] **Step 1: Write failing registry and Python AST scanner tests**

Add `tests/test_pi_agent_boundaries.py` covering:

```python
from pathlib import Path

from seektalent.providers.pi_agent.boundary_patterns import (
    FORBIDDEN_PROVIDER_OPERATIONS,
    PYTHON_FORBIDDEN_IMPORTS,
    PYTHON_FORBIDDEN_OPERATION_MARKERS,
    TYPESCRIPT_PROVIDER_ACTION_FORBIDDEN_OPERATION_MARKERS,
    TYPESCRIPT_SESSION_LIFECYCLE_ALLOWED_OPERATION_MARKERS,
    TYPESCRIPT_FORBIDDEN_OPERATION_MARKERS,
)
from seektalent.providers.liepin.pi_skills import DIRECT_REQUEST_FORBIDDEN_ACTIONS
from tools.check_pi_agent_boundaries import (
    collect_python_boundary_scan_files,
    find_forbidden_python_boundary_patterns,
)


def test_liepin_skill_recipe_reuses_canonical_forbidden_operations() -> None:
    assert DIRECT_REQUEST_FORBIDDEN_ACTIONS == FORBIDDEN_PROVIDER_OPERATIONS
    assert "page.request" in FORBIDDEN_PROVIDER_OPERATIONS
    assert "route.fetch" in FORBIDDEN_PROVIDER_OPERATIONS
    assert "page.evaluate" in FORBIDDEN_PROVIDER_OPERATIONS
    assert "CDPSession" in FORBIDDEN_PROVIDER_OPERATIONS
    assert "requests" in PYTHON_FORBIDDEN_IMPORTS
    assert "evaluate_script" in TYPESCRIPT_FORBIDDEN_OPERATION_MARKERS
    assert "fetch" in TYPESCRIPT_PROVIDER_ACTION_FORBIDDEN_OPERATION_MARKERS
    assert "storageState" in TYPESCRIPT_PROVIDER_ACTION_FORBIDDEN_OPERATION_MARKERS
    assert "storageState" in TYPESCRIPT_SESSION_LIFECYCLE_ALLOWED_OPERATION_MARKERS


def test_python_ast_scan_finds_raw_http_client_imports() -> None:
    files = {
        "src/seektalent/providers/pi_agent/example.py": (
            "import requests\n"
            "import httpx\n"
            "from urllib import request\n"
        ),
    }

    findings = find_forbidden_python_boundary_patterns(files)

    assert ("src/seektalent/providers/pi_agent/example.py", "requests") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "httpx") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "urllib.request") in findings


def test_python_ast_scan_finds_playwright_request_and_network_interception() -> None:
    files = {
        "src/seektalent/providers/pi_agent/example.py": (
            "page.request.get('/api')\n"
            "page.context.request.post('/api')\n"
            "playwright.request.new_context()\n"
            "page.route('**/api/**', handler)\n"
            "page.wait_for_response('**/api/**')\n"
            "page.on('request', handler)\n"
        ),
    }

    findings = find_forbidden_python_boundary_patterns(files)

    assert ("src/seektalent/providers/pi_agent/example.py", "page.request") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "page.context.request") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "playwright.request.new_context") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "page.route") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "page.wait_for_response") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "page.on(request)") in findings


def test_python_ast_scan_finds_script_eval_cookie_storage_and_cdp() -> None:
    files = {
        "src/seektalent/providers/pi_agent/example.py": (
            "page.evaluate('fetch(\"/api/resume\")')\n"
            "page.evaluate_handle('document.cookie')\n"
            "page.add_init_script('localStorage.setItem(\"x\", \"y\")')\n"
            "context.add_cookies([])\n"
            "context.set_extra_http_headers({})\n"
            "context.storage_state(path='auth.json')\n"
            "context.new_cdp_session(page)\n"
        ),
    }

    findings = find_forbidden_python_boundary_patterns(files)

    assert ("src/seektalent/providers/pi_agent/example.py", "page.evaluate") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "page.evaluate_handle") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "page.add_init_script") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "context.add_cookies") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "context.set_extra_http_headers") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "context.storage_state") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "context.new_cdp_session") in findings


def test_python_ast_scan_finds_one_hop_forbidden_aliases() -> None:
    files = {
        "src/seektalent/providers/pi_agent/example.py": (
            "req = page.request\n"
            "ctx_req = page.context.request\n"
            "eval_fn = page.evaluate\n"
            "req.get('/api')\n"
            "ctx_req.post('/api')\n"
            "eval_fn('document.cookie')\n"
        ),
    }

    findings = find_forbidden_python_boundary_patterns(files)

    assert ("src/seektalent/providers/pi_agent/example.py", "page.request") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "page.context.request") in findings
    assert ("src/seektalent/providers/pi_agent/example.py", "page.evaluate") in findings


def test_python_ast_scan_ignores_comments_and_inert_strings() -> None:
    files = {
        "src/seektalent/providers/pi_agent/example.py": (
            "# page.request is only documented here\n"
            "note = 'page.request and route.fetch are inert text'\n"
            "await_safe_click = 'await page.get_by_text(\"Next\").click()'\n"
        ),
    }

    assert find_forbidden_python_boundary_patterns(files) == []


def test_python_boundary_scan_passes_current_source_roots() -> None:
    files = collect_python_boundary_scan_files(root=Path.cwd())

    assert find_forbidden_python_boundary_patterns(files) == []
```

- [ ] **Step 2: Write failing Liepin URL matcher hardening tests**

Extend `tests/test_pi_agent_boundaries.py` or `tests/test_liepin_pi_skills.py` to assert:

```python
def test_liepin_skill_url_matcher_rejects_api_ajax_graphql_download_and_export_routes() -> None:
    skill = get_liepin_pi_skill(PiAgentTaskType.LIEPIN_SEARCH_CARDS)

    assert is_liepin_skill_url_allowed(skill, "https://www.liepin.com/zhaopin/?key=python")
    assert is_liepin_skill_url_allowed(skill, "https://www.liepin.com/lptjob/")
    assert not is_liepin_skill_url_allowed(skill, "https://www.liepin.com/api/search")
    assert not is_liepin_skill_url_allowed(skill, "https://www.liepin.com/ajax/search")
    assert not is_liepin_skill_url_allowed(skill, "https://www.liepin.com/graphql")
    assert not is_liepin_skill_url_allowed(skill, "https://www.liepin.com/resume/download")
    assert not is_liepin_skill_url_allowed(skill, "https://www.liepin.com/export/candidates")
    assert not is_liepin_skill_url_allowed(skill, "https://api-c.liepin.com/zhaopin/")
    assert not is_liepin_skill_url_allowed(skill, "https://www.liepin.com/zhaopin/?next=/api/search")
    assert not is_liepin_skill_url_allowed(skill, "https://www.liepin.com/zhaopin/?next=%2Fapi%2Fsearch")
    assert not is_liepin_skill_url_allowed(skill, "https://www.liepin.com/API/search")
    assert not is_liepin_skill_url_allowed(skill, "https://www.liepin.com/zhaopin/?redirect=https%3A%2F%2Fapi-c.liepin.com%2Fresume")
```

- [ ] **Step 3: Write failing Bun AST checker tests**

Extend `apps/liepin-worker/tests/boundaries.test.ts` with positive violations:

```ts
tools.list_network_requests();
tools.get_network_request("request_1");
tools.evaluate_script("document.cookie");
list_network_requests();
get_network_request("request_1");
evaluate_script("document.cookie");

await page.route("**/api/**", route => route.fetch());
await browserContext.route("**/api/**", route => route.continue({ headers: {} }));
await route.fetch();
await route.continue({ method: "POST" });
await route.fulfill({ body: "raw" });
await page.waitForResponse("**/api/**");
page.on("request", request => console.log(request.url()));
page.on("response", response => console.log(response.url()));

await page.evaluate(() => fetch("/api/resume"));
await page.evaluateHandle(() => document.cookie);
await locator.evaluate(node => node.textContent);
await elementHandle.evaluate(node => node.textContent);
await page.addInitScript(() => localStorage.setItem("x", "y"));
await browserContext.addInitScript(() => sessionStorage.clear());
await browserContext.addCookies([]);
await browserContext.setExtraHTTPHeaders({});
await browserContext.storageState({ path: "auth.json" });
await browserContext.newCDPSession(page);

fetch("/api/resume");
new XMLHttpRequest();
```

Keep negative controls:

```ts
await page.getByText("Next").click();
await page.locator("input[name=q]").fill("大模型 RAG Python");
await page.goto("https://www.liepin.com/zhaopin/?key=python");
```

Add path/profile-sensitive coverage so strict provider-action rules do not break legitimate login/session bootstrap code:

```ts
const sessionLifecycleSource = `
  async function complete(session: any, contextOptions: any, storageState: any) {
    const state = await session.context.storageState();
    contextOptions.storageState = storageState;
    return state;
  }
`;
expect(findBoundaryViolationsInSource(sessionLifecycleSource, "src/loginRelay.ts")).toEqual([]);

const providerActionSource = `
  async function run(page: any, browserContext: any) {
    await browserContext.storageState({ path: "auth.json" });
    fetch("/api/resume");
    new XMLHttpRequest();
  }
`;
expect(findBoundaryViolationsInSource(providerActionSource, "src/cardSearch.ts").length).toBeGreaterThan(0);
```

- [ ] **Step 4: Add the canonical cross-language registry**

Create `src/seektalent/providers/pi_agent/boundary_registry.json`:

```json
{
  "schema_version": "pi-agent-boundary-registry-v1",
  "forbidden_operation_labels": [
    "direct_authenticated_api_replay",
    "network_inspection",
    "network_interception",
    "arbitrary_in_page_script_evaluation",
    "cookie_header_storage_injection",
    "cdp_access",
    "stealth_or_proxy_evasion"
  ],
  "skill_forbidden_operations": [
    "page.request",
    "browserContext.request",
    "context.request",
    "browser_context.request",
    "page.context.request",
    "playwright.request.newContext",
    "playwright.request.new_context",
    "APIRequestContext",
    "page.route",
    "browserContext.route",
    "browser_context.route",
    "route.fetch",
    "route.continue",
    "route.fulfill",
    "page.waitForResponse",
    "page.wait_for_response",
    "page.on(request)",
    "page.on(response)",
    "list_network_requests",
    "get_network_request",
    "evaluate_script",
    "page.evaluate",
    "page.evaluateHandle",
    "page.evaluate_handle",
    "locator.evaluate",
    "elementHandle.evaluate",
    "element_handle.evaluate",
    "page.addInitScript",
    "page.add_init_script",
    "browserContext.addInitScript",
    "browser_context.add_init_script",
    "setExtraHTTPHeaders",
    "set_extra_http_headers",
    "addCookies",
    "add_cookies",
    "storageState",
    "storage_state",
    "CDPSession",
    "newCDPSession",
    "new_cdp_session",
    "Runtime.evaluate",
    "Network.getResponseBody",
    "fetch",
    "XMLHttpRequest",
    "requests",
    "httpx",
    "aiohttp",
    "urllib.request",
    "provider_signature_generation",
    "stealth_plugin",
    "proxy_rotation",
    "header_or_cookie_injection"
  ],
  "python_forbidden_imports": [
    "requests",
    "httpx",
    "aiohttp",
    "urllib.request"
  ],
  "python_forbidden_operation_markers": [
    "page.request",
    "page.context.request",
    "playwright.request.new_context",
    "page.route",
    "page.wait_for_response",
    "page.on(request)",
    "page.on(response)",
    "page.evaluate",
    "page.evaluate_handle",
    "page.add_init_script",
    "context.add_cookies",
    "context.set_extra_http_headers",
    "context.storage_state",
    "context.new_cdp_session",
    "Runtime.evaluate",
    "Network.getResponseBody"
  ],
  "typescript_forbidden_operation_markers": [
    "page.request",
    "browserContext.request",
    "context.request",
    "playwright.request.newContext",
    "APIRequestContext",
    "list_network_requests",
    "get_network_request",
    "evaluate_script",
    "page.route",
    "browserContext.route",
    "route.fetch",
    "route.continue",
    "route.fulfill",
    "page.waitForResponse",
    "page.on(request)",
    "page.on(response)",
    "page.evaluate",
    "page.evaluateHandle",
    "locator.evaluate",
    "elementHandle.evaluate",
    "page.addInitScript",
    "browserContext.addInitScript",
    "browserContext.addCookies",
    "browserContext.setExtraHTTPHeaders",
    "browserContext.storageState",
    "CDPSession",
    "newCDPSession",
    "fetch",
    "XMLHttpRequest"
  ],
  "typescript_provider_action_forbidden_operation_markers": [
    "browserContext.storageState",
    "fetch",
    "XMLHttpRequest"
  ],
  "typescript_session_lifecycle_allowed_operation_markers": [
    "session.context.storageState",
    "contextOptions.storageState"
  ],
  "allowlist_paths": [
    "src/seektalent/providers/pi_agent/boundary_registry.json",
    "src/seektalent/providers/pi_agent/boundary_patterns.py"
  ]
}
```

Create `src/seektalent/providers/pi_agent/boundary_patterns.py` as a small JSON loader that exposes:

- `FORBIDDEN_PROVIDER_OPERATIONS`
- `PYTHON_FORBIDDEN_IMPORTS`
- `PYTHON_FORBIDDEN_OPERATION_MARKERS`
- `TYPESCRIPT_PROVIDER_ACTION_FORBIDDEN_OPERATION_MARKERS`
- `TYPESCRIPT_SESSION_LIFECYCLE_ALLOWED_OPERATION_MARKERS`
- `TYPESCRIPT_FORBIDDEN_OPERATION_MARKERS`
- `BOUNDARY_PATTERN_DECLARATION_PATHS`

The loader must use explicit registry keys. Do not derive Python or TypeScript subsets from marker names.

Modify `src/seektalent/providers/liepin/pi_skills.py`:

```python
from seektalent.providers.pi_agent.boundary_patterns import FORBIDDEN_PROVIDER_OPERATIONS

DIRECT_REQUEST_FORBIDDEN_ACTIONS = FORBIDDEN_PROVIDER_OPERATIONS
```

- [ ] **Step 5: Implement the AST-first Python scanner**

Add `tools/check_pi_agent_boundaries.py` using Python `ast`. It must:

- scan only Python provider automation roots:
  - `src/seektalent/providers/pi_agent`
  - `src/seektalent/providers/liepin`
- reject raw HTTP imports: `requests`, `httpx`, `aiohttp`, `urllib.request`;
- reject Playwright request context usage, including attribute chains and `new_context`;
- reject route interception and response/request listening;
- reject script evaluation and init-script injection;
- reject cookie/header/storage manipulation;
- reject CDP session and network-body access names;
- reject one-hop aliases assigned from forbidden owners, such as `req = page.request`, `ctx_req = page.context.request`, and `eval_fn = page.evaluate`;
- ignore comments and inert string literals;
- skip canonical registry declaration files from `BOUNDARY_PATTERN_DECLARATION_PATHS`;
- expose `find_forbidden_python_boundary_patterns(files: dict[str, str]) -> list[tuple[str, str]]`;
- expose `collect_python_boundary_scan_files(root: Path = Path(".")) -> dict[str, str]`;
- print stable findings and return nonzero in `main()` when violations exist.

This scanner must not be a substring scanner. A limited literal check is acceptable only for names that cannot be represented cleanly in Python AST, and those checks must still avoid comments and inert strings.

- [ ] **Step 6: Harden the Liepin route classifier**

Update `src/seektalent/providers/liepin/pi_skills.py` so `is_liepin_skill_url_allowed()` rejects route classes that represent direct data/API/export surfaces even when the host is allowed:

- path segments: `api`, `ajax`, `graphql`, `download`, `export`;
- hosts outside the skill allowlist, including `api-*` Liepin hosts;
- suspicious query values pointing at API/AJAX/export/download routes, including URL-encoded values and mixed-case route names.

Do not replace the existing pre-action/post-action route distinction.

- [ ] **Step 7: Align the Bun worker boundary check without losing AST precision**

Open `apps/liepin-worker/scripts/checkBoundaries.ts` and keep the existing AST checks for Playwright `request`, `APIRequestContext`, computed request access, destructuring, and OpenCLI imports.

Add registry-backed AST checks for:

- DokoBot/DevTools tool names: `list_network_requests`, `get_network_request`, `evaluate_script`;
- Playwright route/network methods: `route`, `fetch`, `continue`, `fulfill`, `waitForResponse`, `on("request")`, `on("response")`;
- script evaluation: `evaluate`, `evaluateHandle`, `addInitScript`;
- cookie/header/storage manipulation: `addCookies`, `setExtraHTTPHeaders`, `storageState`;
- CDP: `CDPSession`, `newCDPSession`;
- global in-page network primitives inside provider automation code: `fetch`, `XMLHttpRequest`.

The checker must apply explicit scan profiles:

- `provider_action`: strict checks for card search, detail open, extraction, and future PI action modules. `fetch`, `XMLHttpRequest`, `browserContext.storageState`, script evaluation, network interception, CDP, and direct request APIs are forbidden.
- `session_lifecycle`: login relay, session store, and worker bootstrap code may use the narrow `storageState` flow required to persist and inject verified user browser state. This profile still forbids direct request APIs, route interception, network inspection, script evaluation, CDP, cookie/header mutation beyond the established session-store path, and raw provider API calls.
- `test_fixture`: inert strings and redaction fixtures are not executable violations, but executable snippets used to test the boundary checker must still be detected when passed to `findBoundaryViolationsInSource()`.

Use the TypeScript compiler API. Do not replace the checker with substring matching.

- [ ] **Step 8: Run full PI boundary verification**

```bash
uv run pytest tests/test_pi_agent_contracts.py tests/test_liepin_pi_skills.py tests/test_dokobot_capabilities.py tests/test_liepin_detail_policy.py tests/test_pi_agent_artifacts.py tests/test_pi_agent_boundaries.py tests/test_liepin_provider_adapter.py -q
uv run python tools/check_pi_agent_boundaries.py
cd apps/liepin-worker && bun test tests/boundaries.test.ts && bun run boundary-check
git diff --check
```

Expected: pass.

- [ ] **Step 9: Commit boundary guardrails**

```bash
git add src/seektalent/providers/pi_agent/boundary_registry.json src/seektalent/providers/pi_agent/boundary_patterns.py src/seektalent/providers/liepin/pi_skills.py tools/check_pi_agent_boundaries.py tests/test_pi_agent_boundaries.py apps/liepin-worker/scripts/checkBoundaries.ts apps/liepin-worker/tests/boundaries.test.ts
git commit -m "test: enforce pi agent browser boundaries"
```

## Self-Review

- Spec coverage: this plan covers only direct API replay/browser-boundary guardrails and legacy worker compatibility verification.
- Scanner safety: Python boundary scanning is AST-first and must not create a false sense of security from substring-only grep.
- False-positive safety: comments, inert strings, and canonical registry declarations are not executable violations.
- Drift safety: one JSON registry is the canonical source for skill recipe forbidden operations and scanner/checker tests.
- Bun safety: the plan preserves the existing AST-based worker checker and adds missing route/network/evaluate/cookie/CDP checks.
- Route safety: Liepin route matching rejects API/AJAX/GraphQL/download/export classes instead of trusting prefix matches alone.
- Placeholder scan: every step names concrete files, tests, commands, and expected outcomes.
