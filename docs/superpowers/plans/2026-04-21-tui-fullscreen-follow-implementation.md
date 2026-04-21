# SeekTalent Full-Screen TUI Follow Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stream-style TUI with a full-screen prompt-toolkit TUI that owns scrolling/follow mode, removes duplicate input display, speeds up shimmer, and renders a short non-blocking resume-quality comment.

**Architecture:** Keep runtime search behavior unchanged and add only display progress data. `src/seektalent/tui.py` owns transcript/input/status state and rendering. A small `ResumeQualityCommenter` generates an optional display-only comment from top representative scorecards using `openai-chat:deepseek-chat`; failures are captured into progress payload and do not stop reflection.

**Tech Stack:** Python 3.12, prompt-toolkit, pydantic-ai, pytest, existing `WorkflowRuntime` progress callback.

---

## File Map

- Modify `src/seektalent/tui.py`: full-screen app, transcript state, scroll/follow logic, faster shimmer, single input transcript rendering.
- Create `src/seektalent/resume_quality.py`: display-only quality-comment generation and cleanup helpers.
- Modify `src/seektalent/config.py`: add `tui_summary_model` setting defaulting to `openai-chat:deepseek-chat`.
- Modify `src/seektalent/runtime/orchestrator.py`: call comment generator after scoring, include `resume_quality_comment` and `resume_quality_comment_error` in round progress payload.
- Modify `tests/test_tui.py`: transcript, scroll, shimmer, render-order tests.
- Create `tests/test_resume_quality.py`: comment cleanup and prompt payload behavior.
- Modify `tests/test_runtime_audit.py`: success and failure payload tests for the optional comment.

## Task 1: TUI State And Rendering

**Files:**
- Modify: `src/seektalent/tui.py`
- Test: `tests/test_tui.py`

- [ ] **Step 1: Write failing tests for scroll/follow and single transcript display**

Add tests for:

```python
def test_transcript_state_stops_following_when_user_scrolls_up() -> None:
    state = TuiState()
    state.append_lines([f"line {index}" for index in range(20)])
    state.scroll_to_bottom(view_height=5)
    state.scroll_up(3, view_height=5)
    before = state.scroll_offset
    state.append_lines(["new line"])
    assert state.follow is False
    assert state.scroll_offset == before


def test_transcript_state_resumes_following_near_bottom() -> None:
    state = TuiState()
    state.append_lines([f"line {index}" for index in range(20)])
    state.scroll_to_bottom(view_height=5)
    state.scroll_up(5, view_height=5)
    state.scroll_down(4, view_height=5)
    assert state.follow is True


def test_submitted_inputs_render_once() -> None:
    state = TuiState()
    state.submit_input("Job Title", "AI agent开发")
    assert "\n".join(state.transcript_lines).count("AI agent开发") == 1
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest tests/test_tui.py::test_transcript_state_stops_following_when_user_scrolls_up tests/test_tui.py::test_transcript_state_resumes_following_near_bottom tests/test_tui.py::test_submitted_inputs_render_once -q
```

Expected: FAIL because `TuiState` and new methods do not exist.

- [ ] **Step 3: Implement minimal `TuiState`**

Add a dataclass with `transcript_lines`, `scroll_offset`, `follow`, `submit_input`, `append_lines`, `scroll_up`, `scroll_down`, `scroll_to_bottom`, and `visible_lines`.

- [ ] **Step 4: Run focused tests**

Run the command from Step 2. Expected: PASS.

## Task 2: Full-Screen Prompt-Toolkit App

**Files:**
- Modify: `src/seektalent/tui.py`
- Test: `tests/test_tui.py`

- [ ] **Step 1: Write failing tests for shimmer speed and render order**

Add tests for:

```python
def test_shimmer_config_is_faster() -> None:
    assert SHIMMER_REFRESH_PER_SECOND >= 20
    assert SHIMMER_CHARS_PER_SECOND >= 20


def test_quality_comment_renders_after_candidates_before_reflection() -> None:
    event = ProgressEvent(...)
    rendered = "\n".join(_render_progress_lines(event))
    assert rendered.index("代表候选人") < rendered.index("本轮简历质量")
    assert rendered.index("本轮简历质量") < rendered.index("本轮反思")
```

- [ ] **Step 2: Run tests and verify they fail**

Expected: FAIL because constants/comment rendering do not exist.

- [ ] **Step 3: Replace stream session with full-screen session**

Implement `TuiSession` around `prompt_toolkit.Application(full_screen=True)`:

- transcript window uses `FormattedTextControl`
- input window uses `BufferControl`
- status window uses a prompt-toolkit formatted text control
- keybindings: Enter submit/exit when done, Ctrl+J newline, Ctrl+C interrupt, Up/PageUp scroll up, Down/PageDown scroll down, End follow bottom, q exits when done
- progress callback appends rendered progress lines and updates status

- [ ] **Step 4: Run TUI tests**

Run:

```bash
uv run pytest tests/test_tui.py -q
```

Expected: PASS.

## Task 3: Resume Quality Commenter

**Files:**
- Create: `src/seektalent/resume_quality.py`
- Modify: `src/seektalent/config.py`
- Test: `tests/test_resume_quality.py`

- [ ] **Step 1: Write failing tests for comment cleanup and model config**

Add tests for:

```python
def test_clean_quality_comment_collapses_and_truncates() -> None:
    text = clean_quality_comment("  第一行\n第二行" + "好" * 100)
    assert "\n" not in text
    assert len(text) <= 80


def test_settings_has_tui_summary_model_default() -> None:
    assert AppSettings().tui_summary_model == "openai-chat:deepseek-chat"
```

- [ ] **Step 2: Run tests and verify they fail**

Expected: FAIL because module/setting does not exist.

- [ ] **Step 3: Implement `ResumeQualityCommenter`**

Add:

- `clean_quality_comment(text: str) -> str`
- `build_quality_comment_payload(...) -> dict[str, object]`
- `ResumeQualityCommenter.comment(...) -> str`

Use pydantic-ai `Agent` with `build_model(settings.tui_summary_model)` and no structured output.

- [ ] **Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/test_resume_quality.py -q
```

Expected: PASS.

## Task 4: Runtime Progress Payload

**Files:**
- Modify: `src/seektalent/runtime/orchestrator.py`
- Modify: `tests/test_runtime_audit.py`

- [ ] **Step 1: Write failing runtime tests**

Add one test where a stub commenter returns `"整体质量较高，工程经验集中，少数候选人 Agent 深度不足。"` and assert `round_completed.payload["resume_quality_comment"]` contains it.

Add one test where a stub commenter raises and assert:

- `resume_quality_comment is None`
- `resume_quality_comment_error` is present
- `round_completed` is still emitted

- [ ] **Step 2: Run tests and verify they fail**

Run the two new tests. Expected: FAIL because runtime does not call the commenter.

- [ ] **Step 3: Implement runtime integration**

Add `self.resume_quality_commenter = ResumeQualityCommenter(settings)` in `WorkflowRuntime.__init__`.

After scoring and before reflection, call it with the sorted scored candidates for the round. Catch `Exception`, store the error string, and continue.

Add both fields to `_build_round_progress_payload`.

- [ ] **Step 4: Run runtime tests**

Run:

```bash
uv run pytest tests/test_runtime_audit.py::test_runtime_emits_tui_progress_events -q
```

Expected: PASS.

## Task 5: Verification

**Files:**
- All changed files

- [ ] **Step 1: Run CI-equivalent checks**

Run:

```bash
uv run --group dev python tools/check_arch_imports.py
uv run --group dev ruff check src tests experiments
uv run --group dev ty check src tests
uv run --group dev python -m pytest -q
```

Expected: all PASS.

- [ ] **Step 2: Inspect git diff**

Run:

```bash
git status --short
git diff --stat
```

Expected: only planned files changed.
