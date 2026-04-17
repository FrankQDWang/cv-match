from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = PROJECT_ROOT / "src" / "seektalent"
FORBIDDEN_ROOTS = ("seektalent_ui", "experiments")


def _import_root(name: str) -> str:
    return name.split(".", 1)[0]


def _forbidden_imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    failures: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _import_root(alias.name) in FORBIDDEN_ROOTS:
                    failures.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if _import_root(node.module) in FORBIDDEN_ROOTS:
                failures.append((node.lineno, node.module))
    return failures


def main() -> int:
    failures: list[str] = []
    for path in sorted(CORE_SRC.rglob("*.py")):
        for line_no, module_name in _forbidden_imports(path):
            relative_path = path.relative_to(PROJECT_ROOT)
            failures.append(f"{relative_path}:{line_no}: forbidden import {module_name}")
    if failures:
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
