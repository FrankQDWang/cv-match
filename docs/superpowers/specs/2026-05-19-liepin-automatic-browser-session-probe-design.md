# Liepin Automatic Browser Session Probe Design

## Summary

SeekTalent's local Workbench should treat Liepin as a browser-backed source that uses the user's existing local Chrome login state through the Pi agent and DokoBot tooling. When a session includes Liepin and the recruiter starts the agent, the backend should automatically probe whether the Pi/DokoBot execution path can see a valid Liepin session. A successful probe binds the existing Workbench source connection and allows the Liepin lane to run. A failed probe blocks only the Liepin lane with a clear recruiter-facing status while CTS can continue.

This replaces the current product mismatch where the UI says the user must "connect" Liepin even when the user is already logged into Liepin in local Chrome. It must not add a new button, must not revive the old managed-browser login relay in the Svelte Workbench, and must not let Runtime or Workbench directly read Chrome cookies or DokoBot state.

## Problem

The repository already has the lower-level pieces:

- `LiepinPiWorkerClient.session_status(...)` calls `PiLiepinExecutor.probe_session(...)`.
- The Pi-first spec says the user is expected to already be logged into Liepin in the browser profile used by DokoBot.
- `WorkbenchStore.mark_liepin_connection_connected(...)` can persist a connected Liepin connection with a provider account hash.
- The runtime bridge already requires a connected Liepin connection before executing the card source lane.

The missing product behavior is the automatic bridge between "user is logged into local Chrome" and "Workbench has a connected Liepin source connection." Today `POST /api/workbench/sessions/{session_id}/start` calls `WorkbenchStore.start_source_run_job(...)`, and that method blocks Liepin unless a connected Workbench source connection already exists. The source start path does not first ask the Pi/DokoBot lane whether the local browser session is ready.

## Goals

- Starting a session that includes Liepin automatically probes the existing local browser login state through the configured Liepin worker client.
- The probe runs only through the product execution path: Workbench route -> Liepin worker client -> Pi executor -> DokoBot inside Pi. Codex-side Chrome/DokoBot tools are not part of the product.
- If the probe is ready, Workbench persists a connected Liepin source connection, records provider session metadata through the existing Liepin store helpers, and starts the Liepin source run.
- If the probe is not ready, Workbench blocks only the Liepin source run with a safe reason and a clear user-facing message.
- CTS remains independent: a blocked Liepin lane must not prevent CTS from running.
- The Svelte Workbench keeps a passive status display. It does not show a "connect Liepin" or "probe Liepin" action in the primary recruiter flow.
- No public API response, event, running note, or UI surface exposes cookies, raw browser state, raw provider account identifiers, raw DokoBot output, or local artifact paths.

## Non-Goals

- Do not implement manual Liepin login UI.
- Do not revive `/login/frame`, `/login/snapshot`, `/login/input`, or `/login/complete` in the Svelte primary flow.
- Do not install Pi, DokoBot, or a Chrome extension from inside SeekTalent.
- Do not change detail-open approval or budget logic.
- Do not introduce A2A or a new generic agent protocol.
- Do not make Runtime inspect Chrome, DokoBot, or browser cookies directly.
- Do not add compatibility fallback from Pi/DokoBot to the legacy managed-browser relay.

## Product Contract

When a recruiter selected Liepin and clicks "启动 Agent":

1. Workbench checks requirement triage approval as it does today.
2. For each Liepin source run that is not terminal, Workbench gets or creates the user's Liepin source connection.
3. Workbench calls `LiepinWorkerClient.session_status(...)` with the connection id and the existing provider account hash if one is already bound.
4. If the worker reports `ready` with a provider account hash:
   - Workbench creates or reuses the compliance gate for the connection.
   - Workbench records provider session metadata with the existing protected Liepin store helper.
   - Workbench marks the source connection as `connected`.
   - Workbench clears login blocking only for the current `session_id` + `source_run_id`.
   - Workbench starts the Liepin source run job.
5. If the worker reports `login_required`, `missing`, `revoked`, or raises a worker-mode error:
   - Workbench leaves the source connection unconnected.
   - Workbench marks the Liepin source run blocked.
   - Workbench returns a blocked source reason in the start response.
   - Workbench displays a recruiter-facing message that says the user should keep Liepin logged in in local Chrome and retry the agent start.

The user does not press a second "connect" button. The source start is the trigger for the probe.

## State And Reason Mapping

| Worker outcome | Connection state | Source run state | Safe blocked reason | User-facing copy intent |
| --- | --- | --- | --- | --- |
| `ready` with provider hash | `connected` | queued/running after start | none | "Liepin browser session is ready." |
| `login_required` | `login_required` | `blocked` | `liepin_browser_login_required` | "请在本机 Chrome 登录猎聘并保持会话有效，系统会在检索时使用该登录态。" |
| `missing` or `revoked` | `login_required` | `blocked` | `liepin_browser_login_required` | Same as login required. |
| `LiepinWorkerModeError` with `code` or `setup_status` `blocked_backend_unavailable` or `disabled` | previous or `login_required` | `blocked` | `liepin_browser_probe_unavailable` | "浏览器检索通道暂不可用，请确认本机应用和浏览器助手正常后重试。" |
| provider hash mismatch | `login_required` | `blocked` | `liepin_browser_account_mismatch` | "当前 Chrome 中的猎聘账号与此工作台绑定不一致，请切换账号后重试。" |

The public payload must use only these safe reason codes. Raw exception text must not appear in Workbench responses or Svelte UI.

## Security Boundary

- Workbench may persist `provider_account_hash`; it must never persist or expose raw provider account identifiers.
- Pi/DokoBot may inspect the browser session only inside the configured provider execution boundary.
- Runtime and Workbench must not directly call Codex Chrome, Codex DokoBot, local Chrome debugging endpoints, cookie stores, or browser profile files.
- Probe failures must fail closed. If the probe cannot run, Liepin is blocked and CTS may continue.
- The Svelte UI may display status and safe instructions, but must not expose artifact refs, local paths, cookies, tokens, raw provider payloads, or raw Pi output.

## UX Contract

The recruiter-facing source card should say:

- Liepin is using the local Chrome login state.
- If blocked, the user should log into Liepin in local Chrome and retry starting the agent.
- If the browser execution channel is unavailable, the user should check the local app and browser helper setup.

It must not show:

- A "connect Liepin" button in the primary session detail flow.
- Legacy relay terms such as iframe, snapshot, safe frame, managed browser, or handoff.
- Developer data-root posture or local filesystem paths.

## Acceptance Criteria

- Starting a session with Liepin and a fake ready worker creates or reuses the Liepin source connection, marks it connected, and starts the Liepin source run without calling the legacy login endpoints.
- Starting a session with Liepin and a fake ready worker does not change blocked Liepin source runs in other sessions.
- Starting a CTS + Liepin session with a fake login-required worker starts CTS and blocks only Liepin.
- Starting a CTS + Liepin session with a worker-mode error starts CTS and blocks only Liepin with `liepin_browser_probe_unavailable`.
- Starting a Liepin session with a previously bound provider account hash and a probe result for a different provider account hash blocks Liepin with `liepin_browser_account_mismatch`.
- The blocked source run warning uses recruiter-facing copy, not "connection not connected" implementation language.
- Svelte source cards display passive local-Chrome login status and no connection/probe button.
- Tests assert that start responses, source card DOM, security audit events, session events, and global workbench events do not include cookies, raw provider account ids, browser storage state, local artifact paths, or raw Pi/DokoBot output.
- Existing runtime lane execution remains unchanged after the source run is queued.

## Linked Plan

- [2026-05-19-liepin-automatic-browser-session-probe.md](../plans/2026-05-19-liepin-automatic-browser-session-probe.md)
