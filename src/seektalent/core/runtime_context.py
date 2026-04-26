from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeContext:
    workspace_root: Path

    @classmethod
    def from_value(cls, workspace_root: str | Path | None) -> "RuntimeContext":
        root = Path(workspace_root).expanduser() if workspace_root is not None else Path.cwd()
        return cls(workspace_root=root.resolve())

    def resolve_path(self, value: str | Path) -> Path:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        return self.workspace_root / path
