from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from seektalent.config import AppSettings

VALID_PI_COMMAND = (
    "pi --mode rpc --no-session "
    "--extension src/seektalent/providers/pi_agent/pi_extensions/bailian_deepseek.ts "
    "--extension apps/web-svelte/node_modules/pi-mcp-adapter/index.ts"
)


def _write_pi_extension_files(root: Path) -> None:
    provider_extension = root / "src" / "seektalent" / "providers" / "pi_agent" / "pi_extensions"
    provider_extension.mkdir(parents=True, exist_ok=True)
    (provider_extension / "bailian_deepseek.ts").write_text("provider", encoding="utf-8")
    adapter_extension = root / "apps" / "web-svelte" / "node_modules" / "pi-mcp-adapter"
    adapter_extension.mkdir(parents=True, exist_ok=True)
    (adapter_extension / "index.ts").write_text("adapter", encoding="utf-8")


def test_pi_agent_requires_rpc_command_skill_and_dokobot_tool(tmp_path: Path) -> None:
    _write_pi_extension_files(tmp_path)
    skill_path = tmp_path / "liepin_search_cards.md"
    skill_path.write_text("skill", encoding="utf-8")

    settings = AppSettings(
        _env_file=None,
        workspace_root=str(tmp_path),
        liepin_worker_mode="pi_agent",
        liepin_pi_command=VALID_PI_COMMAND,
        liepin_pi_skill_path=str(skill_path),
        liepin_pi_dokobot_tool_name="dokobot",
        liepin_account_binding_secret="runtime-secret",
    )

    assert settings.liepin_worker_mode == "pi_agent"
    assert settings.liepin_pi_command_argv[-2:] == ("--skill", str(skill_path))


def test_pi_agent_rejects_missing_rpc_no_session_or_skill(tmp_path: Path) -> None:
    skill_path = tmp_path / "liepin_search_cards.md"
    skill_path.write_text("skill", encoding="utf-8")

    with pytest.raises(ValueError):
        AppSettings(
            _env_file=None,
            liepin_worker_mode="pi_agent",
            liepin_pi_command="pi --mode json --no-session",
            liepin_pi_skill_path=str(skill_path),
            liepin_pi_dokobot_tool_name="dokobot",
            liepin_account_binding_secret="runtime-secret",
        )


def test_pi_agent_resolves_relative_skill_path_from_workspace_root(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _write_pi_extension_files(workspace)
    skill_path = workspace / "src/seektalent/providers/pi_agent/pi_skills/liepin_search_cards.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("skill", encoding="utf-8")
    old_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        settings = AppSettings(
            _env_file=None,
            workspace_root=str(workspace),
            liepin_worker_mode="pi_agent",
            liepin_pi_command=VALID_PI_COMMAND,
            liepin_pi_skill_path="src/seektalent/providers/pi_agent/pi_skills/liepin_search_cards.md",
            liepin_pi_dokobot_tool_name="dokobot",
            liepin_account_binding_secret="runtime-secret",
        )
    finally:
        os.chdir(old_cwd)

    assert settings.liepin_pi_skill_file_path == skill_path
    assert settings.liepin_pi_command_argv[-1] == str(skill_path)


def test_pi_agent_uses_explicit_repo_local_pi_dependency_path(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _write_pi_extension_files(workspace)
    skill_path = workspace / "src/seektalent/providers/pi_agent/pi_skills/liepin_search_cards.md"
    pi_bin = workspace / "apps/web-svelte/node_modules/.bin/pi"
    skill_path.parent.mkdir(parents=True)
    pi_bin.parent.mkdir(parents=True)
    skill_path.write_text("skill", encoding="utf-8")
    pi_bin.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    pi_bin.chmod(0o755)

    settings = AppSettings(
        _env_file=None,
        workspace_root=str(workspace),
        liepin_worker_mode="pi_agent",
        liepin_pi_command=(
            f"{pi_bin} --mode rpc --no-session "
            "--extension src/seektalent/providers/pi_agent/pi_extensions/bailian_deepseek.ts "
            "--extension apps/web-svelte/node_modules/pi-mcp-adapter/index.ts"
        ),
        liepin_pi_skill_path="src/seektalent/providers/pi_agent/pi_skills/liepin_search_cards.md",
        liepin_pi_dokobot_tool_name="dokobot",
        liepin_account_binding_secret="runtime-secret",
    )

    assert settings.liepin_pi_command_argv[0] == str(pi_bin)


def test_empty_pi_command_uses_default_rpc_command() -> None:
    settings = AppSettings(
        _env_file=None,
        liepin_worker_mode="disabled",
        liepin_pi_command="",
    )

    assert settings.liepin_pi_command == "pi --mode rpc --no-session"


def test_dokobot_action_is_not_a_live_worker_mode() -> None:
    with pytest.raises(ValidationError, match="dokobot_action"):
        AppSettings(_env_file=None, liepin_worker_mode="dokobot_action")


def test_pi_agent_rejects_placeholder_account_binding_secret(tmp_path: Path) -> None:
    skill_path = tmp_path / "liepin_search_cards.md"
    skill_path.write_text("skill", encoding="utf-8")

    with pytest.raises(ValueError, match="liepin_account_binding_secret"):
        AppSettings(
            _env_file=None,
            liepin_worker_mode="pi_agent",
            liepin_pi_command="pi --mode rpc --no-session",
            liepin_pi_skill_path=str(skill_path),
            liepin_pi_dokobot_tool_name="dokobot",
            liepin_account_binding_secret="local-development",
        )


def test_pi_agent_accepts_optional_mcp_config_path(tmp_path: Path) -> None:
    _write_pi_extension_files(tmp_path)
    skill_path = tmp_path / "liepin_search_cards.md"
    mcp_path = tmp_path / ".pi" / "mcp.json"
    skill_path.write_text("Liepin skill", encoding="utf-8")
    settings = AppSettings(
        _env_file=None,
        workspace_root=str(tmp_path),
        liepin_worker_mode="pi_agent",
        liepin_pi_command=VALID_PI_COMMAND,
        liepin_pi_skill_path=str(skill_path),
        liepin_pi_mcp_config_path=str(mcp_path),
        liepin_pi_dokobot_tool_name="dokobot",
        liepin_account_binding_secret="non-placeholder-secret",
    )

    assert settings.liepin_pi_mcp_config_file_path == mcp_path


def test_pi_agent_command_requires_provider_and_mcp_adapter_extensions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEEKTALENT_LIEPIN_WORKER_MODE", "pi_agent")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_ACCOUNT_BINDING_SECRET", "account-secret")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_PI_COMMAND", "pi --mode rpc --no-session")

    with pytest.raises(ValueError, match="required extension"):
        AppSettings(_env_file=None)


def test_pi_agent_command_rejects_missing_provider_extension(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEEKTALENT_LIEPIN_WORKER_MODE", "pi_agent")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_ACCOUNT_BINDING_SECRET", "account-secret")
    monkeypatch.setenv(
        "SEEKTALENT_LIEPIN_PI_COMMAND",
        "pi --mode rpc --no-session --extension apps/web-svelte/node_modules/pi-mcp-adapter/index.ts",
    )

    with pytest.raises(ValueError, match="required extension"):
        AppSettings(_env_file=None)


def test_pi_agent_command_accepts_required_provider_and_mcp_adapter_extensions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_pi_extension_files(tmp_path)
    skill_path = tmp_path / "src" / "seektalent" / "providers" / "pi_agent" / "pi_skills"
    skill_path.mkdir(parents=True)
    (skill_path / "liepin_search_cards.md").write_text("skill", encoding="utf-8")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_WORKER_MODE", "pi_agent")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_ACCOUNT_BINDING_SECRET", "account-secret")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_PI_COMMAND", VALID_PI_COMMAND)
    monkeypatch.setenv("SEEKTALENT_WORKSPACE_ROOT", str(tmp_path))

    settings = AppSettings(_env_file=None)

    assert "src/seektalent/providers/pi_agent/pi_extensions/bailian_deepseek.ts" in settings.liepin_pi_command_argv
    assert "apps/web-svelte/node_modules/pi-mcp-adapter/index.ts" in settings.liepin_pi_command_argv


def test_empty_pi_mcp_config_path_normalizes_to_none(tmp_path: Path) -> None:
    settings = AppSettings(
        _env_file=None,
        workspace_root=str(tmp_path),
        liepin_pi_mcp_config_path="",
    )

    assert settings.liepin_pi_mcp_config_path is None


def test_pi_agent_model_id_is_explicit_root_env_setting(tmp_path: Path) -> None:
    settings = AppSettings(
        _env_file=None,
        workspace_root=str(tmp_path),
        liepin_pi_model_id="deepseek-v4-flash",
    )

    assert settings.liepin_pi_model_id == "deepseek-v4-flash"


def test_liepin_dokobot_mcp_config_defaults_to_unproven(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEEKTALENT_LIEPIN_WORKER_MODE", "disabled")
    monkeypatch.delenv("SEEKTALENT_LIEPIN_DOKOBOT_MCP_COMMAND", raising=False)
    settings = AppSettings(_env_file=None)

    assert settings.liepin_dokobot_mcp_server_name == "dokobot"
    assert settings.liepin_dokobot_mcp_command is None
    assert settings.liepin_dokobot_mcp_args == ()
    assert settings.liepin_dokobot_direct_tools == ()
    assert settings.liepin_dokobot_observed_tools == ()


def test_liepin_dokobot_mcp_json_fields_are_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEEKTALENT_LIEPIN_WORKER_MODE", "disabled")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_DOKOBOT_MCP_SERVER_NAME", "dokobot")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_DOKOBOT_MCP_COMMAND", "dokobot-mcp")
    monkeypatch.setenv("SEEKTALENT_LIEPIN_DOKOBOT_MCP_ARGS_JSON", '["--stdio"]')
    monkeypatch.setenv("SEEKTALENT_LIEPIN_DOKOBOT_DIRECT_TOOLS_JSON", '["read_page","click","type_text"]')
    monkeypatch.setenv(
        "SEEKTALENT_LIEPIN_DOKOBOT_OBSERVED_TOOLS_JSON",
        json.dumps(["dokobot_read_page", "dokobot_click", "dokobot_type_text"]),
    )

    settings = AppSettings(_env_file=None)

    assert settings.liepin_dokobot_mcp_command == "dokobot-mcp"
    assert settings.liepin_dokobot_mcp_args == ("--stdio",)
    assert settings.liepin_dokobot_direct_tools == ("read_page", "click", "type_text")
    assert settings.liepin_dokobot_observed_tools == (
        "dokobot_read_page",
        "dokobot_click",
        "dokobot_type_text",
    )
