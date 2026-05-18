from __future__ import annotations

import json
from pathlib import Path

import pytest

from pydantic import ValidationError
from seektalent.config import AppSettings
from seektalent.dev_mode import build_dev_mode_env_diagnostics, build_dev_mode_status
from seektalent_ui.server import _can_recover_with_dev_mode_env_diagnostics
from tests.settings_factory import make_settings


def test_raw_env_diagnostics_do_not_expose_secret_values(tmp_path: Path) -> None:
    skill_path = tmp_path / "liepin.md"
    env = {
        "SEEKTALENT_TEXT_LLM_API_KEY": "sk-secret-value",
        "SEEKTALENT_CTS_TENANT_KEY": "tenant-key-secret",
        "SEEKTALENT_CTS_TENANT_SECRET": "tenant-secret-value",
        "SEEKTALENT_LIEPIN_WORKER_MODE": "pi_agent",
        "SEEKTALENT_LIEPIN_PI_COMMAND": "pi --mode rpc --no-session --token secret",
        "SEEKTALENT_LIEPIN_PI_SKILL_PATH": str(skill_path),
        "SEEKTALENT_LIEPIN_PI_DOKOBOT_TOOL_NAME": "dokobot",
        "SEEKTALENT_LIEPIN_ACCOUNT_BINDING_SECRET": "account-binding-secret",
    }

    payload = build_dev_mode_env_diagnostics(env, workspace_root=tmp_path).model_dump(mode="json")
    raw = json.dumps(payload, sort_keys=True)

    assert "sk-secret-value" not in raw
    assert "tenant-key-secret" not in raw
    assert "tenant-secret-value" not in raw
    assert "account-binding-secret" not in raw
    assert "--token secret" not in raw
    assert str(skill_path) not in raw
    assert payload["overallStatus"] == "needs_setup"


def test_raw_env_diagnostics_reports_local_data_root_posture(tmp_path: Path) -> None:
    env = {
        "SEEKTALENT_ARTIFACTS_DIR": str(tmp_path / ".seektalent" / "artifacts"),
        "SEEKTALENT_LLM_CACHE_DIR": str(tmp_path / "repo-cache"),
    }
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    payload = build_dev_mode_env_diagnostics(env, workspace_root=tmp_path)
    roots = {root.name: root for root in payload.dataRoots}

    assert roots["artifacts"].status in {"safe", "unknown"}
    assert roots["llm_cache"].status == "warning"
    assert roots["llm_cache"].reasonCode == "inside_repo"


def test_raw_env_diagnostics_reports_pi_agent_missing_config_without_appsettings(tmp_path: Path) -> None:
    payload = build_dev_mode_env_diagnostics(
        {"SEEKTALENT_LIEPIN_WORKER_MODE": "pi_agent"},
        workspace_root=tmp_path,
    )
    components = {component.name: component for component in payload.components}

    assert payload.mode == "raw_env_diagnostics"
    assert payload.overallStatus == "needs_setup"
    assert components["liepin_pi_command"].status == "configured"
    assert components["liepin_pi_skill"].status == "configured"
    assert components["liepin_account_binding_secret"].status == "needs_setup"


def test_raw_env_diagnostics_reports_invalid_pi_command(tmp_path: Path) -> None:
    skill_path = tmp_path / "liepin_search_cards.md"
    skill_path.write_text("Liepin skill", encoding="utf-8")

    payload = build_dev_mode_env_diagnostics(
        {
            "SEEKTALENT_LIEPIN_WORKER_MODE": "pi_agent",
            "SEEKTALENT_LIEPIN_ACCOUNT_BINDING_SECRET": "account-binding-secret",
            "SEEKTALENT_LIEPIN_PI_COMMAND": "pi --no-session",
            "SEEKTALENT_LIEPIN_PI_SKILL_PATH": str(skill_path),
        },
        workspace_root=tmp_path,
    )
    components = {component.name: component for component in payload.components}

    assert payload.overallStatus == "invalid"
    assert components["liepin_pi_command"].status == "invalid"


def test_server_startup_can_fallback_to_readiness_for_invalid_pi_agent_config(tmp_path: Path) -> None:
    skill_path = tmp_path / "liepin_search_cards.md"
    skill_path.write_text("Liepin skill", encoding="utf-8")
    env = {
        "SEEKTALENT_LIEPIN_WORKER_MODE": "pi_agent",
        "SEEKTALENT_LIEPIN_ACCOUNT_BINDING_SECRET": "account-binding-secret",
        "SEEKTALENT_LIEPIN_PI_COMMAND": "pi --no-session",
        "SEEKTALENT_LIEPIN_PI_SKILL_PATH": str(skill_path),
    }

    with pytest.raises(ValidationError) as exc_info:
        AppSettings(_env_file=None, workspace_root=str(tmp_path), **{key.removeprefix("SEEKTALENT_").lower(): value for key, value in env.items()})

    assert _can_recover_with_dev_mode_env_diagnostics(exc_info.value, env)


def test_valid_settings_status_reports_configured_components(tmp_path: Path) -> None:
    skill_path = tmp_path / "liepin_search_cards.md"
    skill_path.write_text("Liepin skill", encoding="utf-8")
    settings = make_settings(
        workspace_root=str(tmp_path),
        text_llm_api_key="sk-live",
        cts_tenant_key="tenant-key",
        cts_tenant_secret="tenant-secret",
        liepin_worker_mode="pi_agent",
        liepin_pi_skill_path=str(skill_path),
        liepin_account_binding_secret="non-placeholder-secret",
    )

    payload = build_dev_mode_status(settings)
    components = {component.name: component for component in payload.components}

    assert payload.mode == "settings"
    assert payload.overallStatus in {"ready", "warning"}
    assert components["text_llm"].status == "configured"
    assert components["cts"].status == "configured"
    assert components["liepin_account_binding_secret"].status == "configured"
