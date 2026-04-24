from __future__ import annotations

import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from seektalent.config import AppSettings
from seektalent.runtime.exact_llm_cache import clear_exact_llm_cache

RUN_DIR_RE = re.compile(r"^\d{8}_\d{6}_[0-9a-f]{8}$")
BENCHMARK_SUMMARY_RE = re.compile(r"^benchmark_summary_(\d{8}_\d{6})\.json$")
PROD_RUN_RETENTION_DAYS = 7


def cleanup_runtime_artifacts(settings: AppSettings, *, now: datetime | None = None) -> None:
    clear_exact_llm_cache(settings)
    if settings.runtime_mode != "prod":
        return
    cleanup_old_run_artifacts(settings.runs_path, now=now or datetime.now(), retention_days=PROD_RUN_RETENTION_DAYS)


def cleanup_old_run_artifacts(runs_root: Path, *, now: datetime, retention_days: int) -> None:
    if not runs_root.exists():
        return
    cutoff = now - timedelta(days=retention_days)
    for path in runs_root.iterdir():
        if path.is_dir() and _run_dir_is_expired(path.name, cutoff):
            shutil.rmtree(path)
            continue
        if path.is_file() and _benchmark_summary_is_expired(path.name, cutoff):
            path.unlink()


def _run_dir_is_expired(name: str, cutoff: datetime) -> bool:
    if not RUN_DIR_RE.fullmatch(name):
        return False
    return _parse_timestamp(name[:15]) < cutoff


def _benchmark_summary_is_expired(name: str, cutoff: datetime) -> bool:
    match = BENCHMARK_SUMMARY_RE.fullmatch(name)
    if match is None:
        return False
    return _parse_timestamp(match.group(1)) < cutoff


def _parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d_%H%M%S")
