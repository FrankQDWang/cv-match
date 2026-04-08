"""seektalent package."""

from seektalent.bootstrap import BootstrapArtifacts, bootstrap_round0, bootstrap_round0_async
from seektalent.api import run_match, run_match_async
from seektalent.config import AppSettings
from seektalent.runtime import RUNTIME_PHASE_GATE_MESSAGE, RuntimePhaseGateError

__all__ = [
    "__version__",
    "AppSettings",
    "BootstrapArtifacts",
    "RUNTIME_PHASE_GATE_MESSAGE",
    "RuntimePhaseGateError",
    "bootstrap_round0",
    "bootstrap_round0_async",
    "run_match",
    "run_match_async",
]

__version__ = "0.3.0a1"
