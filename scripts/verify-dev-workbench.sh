#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

uv run pytest \
  tests/test_dev_mode_readiness.py \
  tests/test_workbench_api.py \
  tests/test_workbench_semantic_guardrails.py \
  tests/test_workbench_dual_source_dev_mode.py \
  tests/test_runtime_source_lanes.py \
  tests/test_liepin_runtime_source_lane.py \
  tests/test_liepin_config.py \
  tests/test_liepin_pi_executor.py \
  tests/test_pi_external_agent.py \
  tests/test_pi_payload_firewall.py \
  -q

uv run ruff check \
  src/seektalent/dev_mode.py \
  src/seektalent_ui/final_top_candidates.py \
  src/seektalent_ui/models.py \
  src/seektalent_ui/workbench_routes.py \
  src/seektalent_ui/server.py \
  src/seektalent_ui/workbench_store.py \
  tests/test_dev_mode_readiness.py \
  tests/test_workbench_api.py \
  tests/test_workbench_semantic_guardrails.py \
  tests/test_workbench_dual_source_dev_mode.py

if [[ "${SEEKTALENT_VERIFY_PYTHON_ONLY:-0}" == "1" ]]; then
  echo "SEEKTALENT_VERIFY_PYTHON_ONLY=1; skipped Svelte verification" >&2
  exit 0
fi

command -v bun >/dev/null 2>&1 || {
  echo "bun not found; rerun with SEEKTALENT_VERIFY_PYTHON_ONLY=1 only for Python-only local checks" >&2
  exit 1
}

tmp_root="$(mktemp -d)"
api_pid=""
cleanup() {
  if [[ -n "$api_pid" ]]; then
    kill "$api_pid" 2>/dev/null || true
  fi
  rm -rf "$tmp_root"
}
trap cleanup EXIT

env SEEKTALENT_WORKSPACE_ROOT="$tmp_root" SEEKTALENT_WORKBENCH_ENABLED=true uv run seektalent-ui-api --host 127.0.0.1 --port 8012 &
api_pid=$!
until curl -fsS http://127.0.0.1:8012/openapi.json >/dev/null; do sleep 0.2; done

schema_path="apps/web-svelte/src/lib/api/schema.d.ts"
schema_before="$(shasum "$schema_path" | awk '{print $1}')"

(
  cd apps/web-svelte
  bun run api:gen
  bun run check
  bun run lint
  bun run test
  bun run build
  bun run test:e2e
)

schema_after="$(shasum "$schema_path" | awk '{print $1}')"
if [[ "$schema_before" != "$schema_after" ]]; then
  echo "Generated OpenAPI schema changed; run bun run api:gen and review the result." >&2
  exit 1
fi

for forbidden in login-relay 'login/snapshot' 'login/frame' server_managed_browser managed_local external_http dokobot_action DokoBotActionSurface DokoBotActionTransportSession pi_runner.py; do
  if rg -n "$forbidden" apps/web-svelte/src --glob '!apps/web-svelte/src/lib/api/schema.d.ts'; then
    echo "Forbidden legacy Liepin browser fallback reference found in Svelte milestone wiring: $forbidden" >&2
    exit 1
  fi
done

git diff --check
