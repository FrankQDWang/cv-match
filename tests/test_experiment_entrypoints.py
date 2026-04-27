from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from seektalent.runtime import WorkflowRuntime
from seektalent.tracing import RunTracer
from tests.settings_factory import make_settings
from tests.test_runtime_state_flow import _install_broaden_stubs, _python_feedback_seed_scorecards, _sample_inputs
from tools.run_global_benchmark import build_policy_comparison_env, build_policy_comparison_settings


@pytest.mark.parametrize(
    ("module", "specific_option"),
    [
        ("experiments.openclaw_baseline.run", "--gateway-base-url"),
        ("experiments.claude_code_baseline.run", "--timeout-seconds"),
        ("experiments.jd_text_baseline.run", "--notes-file"),
    ],
)
def test_experiment_run_module_help_smoke(module: str, specific_option: str) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    pythonpath = [str(repo_root), str(repo_root / "src")]
    if env.get("PYTHONPATH"):
        pythonpath.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)

    result = subprocess.run(
        [sys.executable, "-m", module, "--help"],
        cwd=repo_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert f"python -m {module}" in result.stdout
    for option in ("--job-title", "--jd", "--env-file", "--output-dir", "--json", specific_option):
        assert option in result.stdout


def test_build_policy_comparison_env_primary_disables_company_isolation_flags() -> None:
    env = build_policy_comparison_env(mode="primary")

    assert env["SEEKTALENT_TARGET_COMPANY_ENABLED"] == "false"
    assert env["SEEKTALENT_COMPANY_DISCOVERY_ENABLED"] == "false"


def test_primary_policy_comparison_disables_company_discovery_behavior(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = build_policy_comparison_settings(
        base_settings=make_settings(
            runs_dir=str(tmp_path / "runs"),
            mock_cts=True,
            min_rounds=1,
            max_rounds=10,
            candidate_feedback_enabled=True,
            company_discovery_enabled=True,
            bocha_api_key="bocha-key",
        ),
        mode="primary",
    )
    runtime = WorkflowRuntime(settings)
    _install_broaden_stubs(runtime, include_reserve=False)
    tracer = RunTracer(tmp_path / "trace-runs")
    job_title, jd, notes = _sample_inputs()
    called = {"value": False}

    async def _fail(*args, **kwargs):
        called["value"] = True
        raise AssertionError("company discovery should be disabled in primary comparison")

    monkeypatch.setattr(runtime.company_discovery, "discover_web", _fail)

    try:
        run_state = asyncio.run(runtime._build_run_state(job_title=job_title, jd=jd, notes=notes, tracer=tracer))
        run_state.scorecards_by_resume_id = _python_feedback_seed_scorecards()
        run_state.top_pool_ids = ["fit-1", "fit-2"]
        asyncio.run(runtime._run_rounds(run_state=run_state, tracer=tracer))
    finally:
        tracer.close()

    round_dir = tracer.run_dir / "rounds" / "round_02"
    rescue_decision = json.loads((round_dir / "rescue_decision.json").read_text(encoding="utf-8"))
    assert settings.target_company_enabled is False
    assert settings.company_discovery_enabled is False
    assert rescue_decision["selected_lane"] == "anchor_only"
    assert {"lane": "web_company_discovery", "reason": "disabled"} in rescue_decision["skipped_lanes"]
    assert called["value"] is False
    assert not (round_dir / "company_discovery_result.json").exists()
