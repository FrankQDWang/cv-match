#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path


INLINE_MATH_RE = re.compile(r"\\\((.+?)\\\)")


def replace_inline_math(text: str) -> str:
    return INLINE_MATH_RE.sub(r"$`\1`$", text)


def drop_first_h1(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines) + "\n"


def build_notion_safe_markdown(source: str) -> str:
    return replace_inline_math(drop_first_h1(source))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Notion-safe markdown body from a canonical markdown file."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.source.read_text(encoding="utf-8")
    output = build_notion_safe_markdown(source)
    args.output.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
