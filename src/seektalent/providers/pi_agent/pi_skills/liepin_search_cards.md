---
name: liepin-search-cards
description: Collect Liepin search result cards through Pi-owned browser tools only.
---

# Liepin Card Search

Use only SeekTalent Pi-owned browser tools. Do not call provider APIs directly,
do not replay browser cookies. Do not ask for cookies, tokens, SMS codes,
passwords, localStorage, sessionStorage, or other credentials.

The browser is expected to already be logged in by the user. If login,
permission, captcha, or risk-control blocks the task, stop and return the
blocked JSON envelope.

In card mode:

- Search with the supplied keyword query.
- Preserve the provider search result order.
- Read only the search result card/listing surface.
- Do not open candidate detail pages in card mode.
- Do not click contact, chat, download, phone, email, or resume-detail actions.
- Store protected page traces, provider key material, and snapshots under
  `SEEKTALENT_PI_ARTIFACT_ROOT`.
- Return artifact refs only, never raw HTML, cookies, tokens, contact data, or
  raw resumes.

Return exactly one JSON object as the final assistant message. Do not wrap it in
Markdown and do not include notes before or after it.

Required card fields include `provider_candidate_key_material_ref`,
`safe_card_summary`, `safe_card_summary_ref`, and `protected_snapshot_ref`.

## OpenCLI Browser Mode

When SeekTalent OpenCLI tools are available, use them for both page reading and
page action.

The allowed card-search entry is the recruiter resume-search surface:
`https://h.liepin.com/search/getConditionItem#session`. The
`seektalent_opencli_open_liepin_tab` tool binds the current user Chrome tab and
navigates it to this entry. Do not use owned sessions or tab-management actions
that create a standalone Chrome window.

Allowed tools:

- `seektalent_opencli_status`
- `seektalent_opencli_capabilities`
- `seektalent_opencli_open_liepin_tab`
- `seektalent_opencli_state`
- `seektalent_opencli_get_url`
- `seektalent_opencli_find`
- `seektalent_opencli_fill`
- `seektalent_opencli_click`
- `seektalent_opencli_scroll`
- `seektalent_opencli_wait_time`

Use only short generated search keywords in `seektalent_opencli_fill`. Never
pass the full JD, notes, raw resumes, credentials, cookies, storage, or provider
payloads to browser tools.

Do not use OpenCLI site adapters. Do not use eval, network, upload, download,
cookies, storage, contact, chat, payment, or account settings.

Stop and return a blocked safe envelope on login-required, identity intercept,
captcha, risk page, unknown modal, contact prompt, chat prompt, payment prompt,
download prompt, or detail-open requirement.

## Probe Tasks

For `liepin.probe_capabilities`, do not navigate, click, type, scroll, or open a
page. Call only the safe browser status and capability manifest tools, then
return exactly one `seektalent.pi_capability_probe.v1` JSON object.

For `liepin.probe_session`, return exactly one
`seektalent.pi_liepin_session_probe.v1` JSON object. Never include cookies,
tokens, raw account identifiers, localStorage, sessionStorage, phone numbers, or
email addresses.
