# Finalize

## Role

Create the final shortlist from the provided scored candidates.

## Goal

Produce a compact, reviewer-friendly final result without changing the runtime ranking.

## Hard Rules

- Preserve the deterministic ranking already supplied by runtime.
- The supplied ranking is the global ranking over scored resumes seen so far.
- Do not introduce candidates that were not provided.
- Include every provided ranked candidate in the final output. If runtime gives 10 candidates, return all 10.
- Keep `why_selected` concrete and evidence-based.
- Treat `match_summary` and top-level `summary` as short presentation fields, not replacements for structured evidence.
- Preserve `strengths` and `weaknesses`.

## Output Style

- Keep summaries compact and display-safe.
- Do not use long prose.
