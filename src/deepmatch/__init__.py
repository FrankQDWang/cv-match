"""deepmatch package."""

from deepmatch.api import MatchRunResult, run_match, run_match_async
from deepmatch.config import AppSettings

__all__ = [
    "__version__",
    "AppSettings",
    "MatchRunResult",
    "run_match",
    "run_match_async",
]

__version__ = "0.2.0"
