from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from seektalent.config import AppSettings


def make_settings(**overrides: object) -> AppSettings:
    return cast(Any, AppSettings)(_env_file=None, **overrides)


def make_pi_agent_settings(tmp_path: Path, **overrides: object) -> AppSettings:
    workspace = tmp_path / "workspace"
    provider_extension = workspace / "src" / "seektalent" / "providers" / "pi_agent" / "pi_extensions"
    adapter_extension = workspace / "apps" / "web-svelte" / "node_modules" / "pi-mcp-adapter"
    skill_path = workspace / "src" / "seektalent" / "providers" / "pi_agent" / "pi_skills" / "liepin_search_cards.md"
    provider_extension.mkdir(parents=True, exist_ok=True)
    adapter_extension.mkdir(parents=True, exist_ok=True)
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    (provider_extension / "bailian_deepseek.ts").write_text("provider", encoding="utf-8")
    (adapter_extension / "index.ts").write_text("adapter", encoding="utf-8")
    skill_path.write_text("skill", encoding="utf-8")
    data: dict[str, object] = {
        "workspace_root": str(workspace),
        "liepin_worker_mode": "pi_agent",
        "liepin_account_binding_secret": "runtime-secret",
        "liepin_pi_command": (
            "pi --mode rpc --no-session "
            "--extension src/seektalent/providers/pi_agent/pi_extensions/bailian_deepseek.ts "
            "--extension apps/web-svelte/node_modules/pi-mcp-adapter/index.ts"
        ),
        "liepin_pi_skill_path": "src/seektalent/providers/pi_agent/pi_skills/liepin_search_cards.md",
    }
    data.update(overrides)
    return make_settings(**data)
