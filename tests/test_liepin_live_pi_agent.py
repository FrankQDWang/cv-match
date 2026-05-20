from __future__ import annotations

import json
import os

import pytest

from seektalent.cli import main


@pytest.mark.skipif(
    os.environ.get("SEEKTALENT_LIVE_PI_AGENT") != "1",
    reason="Live Pi/DokoBot smoke requires SEEKTALENT_LIVE_PI_AGENT=1.",
)
def test_live_pi_agent_doctor_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["doctor", "--live-pi-agent", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code in {0, 1}
    assert isinstance(payload.get("checks"), list)
    rendered = json.dumps(payload)
    assert "storageState" not in rendered
    assert "raw_provider_payload" not in rendered
    assert "Authorization" not in rendered
