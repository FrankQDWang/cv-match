from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.markup import escape

from seektalent.api import run_match_async
from seektalent.models import SearchRunBundle
from seektalent.progress import ProgressEvent

PromptFn = Callable[[str], str]
RunSearchFn = Callable[..., Awaitable[SearchRunBundle]]


def run_chat_session(
    *,
    ask: PromptFn | None = None,
    console: Console | None = None,
    run_search: RunSearchFn = run_match_async,
    cwd: Path | None = None,
) -> int:
    console = console or Console()
    prompt = ask or _build_prompt()
    try:
        _print_intro(console, cwd or Path.cwd())
        job_description = _read_job_description(console, prompt)
        console.print()
        console.print(
            "Paste [bold]Hiring Notes[/] if you have them. Press [bold]Enter[/] to skip. "
            "Use [bold]Ctrl+J[/] for new lines."
        )
        hiring_notes = prompt("› ").rstrip().strip()
        console.print()
        console.print("Working:")
        bundle = asyncio.run(
            run_search(
                job_description=job_description,
                hiring_notes=hiring_notes,
                top_k=10,
                round_budget=None,
                env_file=".env",
                progress_callback=lambda event: _print_progress(console, event),
            )
        )
    except KeyboardInterrupt:
        console.print("\nInterrupted. Re-run [bold]seektalent[/] to start a new session.")
        return 130
    except Exception as exc:  # noqa: BLE001
        console.print(f"Run failed.\n{escape(str(exc))}")
        console.print("Session complete. Re-run [bold]seektalent[/] to start a new session.")
        return 1
    console.print()
    console.print(_result_message(bundle))
    console.print()
    console.print("Session complete. Re-run [bold]seektalent[/] to start a new session.")
    return 0


def _build_prompt() -> PromptFn:
    os.environ.setdefault("PROMPT_TOOLKIT_NO_CPR", "1")
    bindings = KeyBindings()

    @bindings.add("enter")
    def _submit(event) -> None:
        event.current_buffer.validate_and_handle()

    @bindings.add("c-j")
    def _newline(event) -> None:
        event.current_buffer.insert_text("\n")

    session = PromptSession(
        multiline=True,
        key_bindings=bindings,
        prompt_continuation=lambda width, line_number, wrap_count: "  ",
        bottom_toolbar=lambda: " Enter submit · Ctrl+J newline · Ctrl+C quit ",
    )
    return session.prompt


def _print_intro(console: Console, cwd: Path) -> None:
    console.print(
        "\n".join(
            [
                "[dim]╭─────────────────────────────────────────────╮[/]",
                "[dim]│[/] [bold]>_[/] [bold]SeekTalent[/]                               [dim]│[/]",
                "[dim]│[/]                                             [dim]│[/]",
                "[dim]│[/] [dim]mode:[/]      chat-first JD search            [dim]│[/]",
                f"[dim]│[/] [dim]cwd:[/]       {escape(str(cwd))[:29]:<29} [dim]│[/]",
                "[dim]╰─────────────────────────────────────────────╯[/]",
                "",
                "Paste [bold]Job Description[/]. Press [bold]Enter[/] to submit. "
                "Use [bold]Ctrl+J[/] for new lines.",
            ]
        )
    )


def _read_job_description(console: Console, prompt: PromptFn) -> str:
    while True:
        text = prompt("› ").rstrip()
        if text.strip():
            return text.strip()
        console.print("Job Description cannot be empty. Paste the JD and press [bold]Enter[/].")


def _print_progress(console: Console, event: ProgressEvent) -> None:
    console.print(f"• {escape(event.message)}")


def _result_message(bundle: SearchRunBundle) -> str:
    cards = bundle.final_result.final_candidate_cards[:10]
    lines = [
        "Run complete.",
        f"stop_reason: {escape(bundle.final_result.stop_reason)}",
        f"reviewer_summary: {escape(bundle.final_result.reviewer_summary)}",
        f"run_summary: {escape(bundle.final_result.run_summary)}",
    ]
    if not cards:
        lines.append("top_candidates: none")
        return "\n".join(lines)
    lines.append("top_candidates:")
    for index, card in enumerate(cards, start=1):
        lines.append(
            f"{index}. {escape(_value(card, 'candidate_id'))} | {escape(_value(card, 'review_recommendation'))}"
        )
        lines.append(f"   {escape(_value(card, 'card_summary'))}")
        gap_text = _signal_summary(_value(card, "gap_signals"))
        risk_text = _signal_summary(_value(card, "risk_signals"))
        if gap_text:
            lines.append(f"   gaps: {gap_text}")
        if risk_text:
            lines.append(f"   risks: {risk_text}")
    return "\n".join(lines)


def _signal_summary(signals: Any) -> str:
    if not signals:
        return ""
    parts = [_signal_text(signal) for signal in signals[:2]]
    return "; ".join(part for part in parts if part)


def _signal_text(signal: Any) -> str:
    if isinstance(signal, dict):
        return escape(str(signal.get("display_text") or signal.get("signal") or ""))
    return escape(str(getattr(signal, "display_text", None) or getattr(signal, "signal", "")))


def _value(item: Any, field: str) -> Any:
    if isinstance(item, dict):
        return item.get(field, "")
    return getattr(item, field, "")


__all__ = ["run_chat_session"]
