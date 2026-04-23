# Retrieval Rescue

Date: 2026-04-23

## Context

SeekTalent now has several ways to recover from weak recall:

- the existing runtime broaden path, including reserve-term broaden and anchor-only search;
- target-company web discovery work on the `codex/target-company-discovery` branch;
- the proposed candidate-derived query expansion based on already scored fit resumes.

These should not become competing controller choices. They should be a single high-level runtime rescue ladder with explicit routing, one-shot execution, and auditable artifacts.

## Product Decision

Default behavior should optimize for low cost and low latency before using external web search.

Default feature flags:

```env
SEEKTALENT_CANDIDATE_FEEDBACK_ENABLED=true
SEEKTALENT_TARGET_COMPANY_ENABLED=false
SEEKTALENT_COMPANY_DISCOVERY_ENABLED=true
```

Meaning:

- Candidate feedback is enabled by default because it uses internal evidence and has low latency.
- Explicit target-company bootstrap is disabled by default because JD and notes often contain mixed intent, shorthand, segment labels, client companies, excluded sources, and ambiguous recruiter language.
- Web company discovery is enabled by default, but only as a later rescue lane after cheaper internal options are unavailable or already attempted.
- Anchor-only/basic search remains available, but only as the final fallback.

## Goals

- Route recall-repair behavior through one runtime-level rescue router.
- Prefer internal, scored evidence before external web discovery.
- Add guarded one-shot candidate feedback expansion.
- Use web discovery only for external market mapping, not for default query rewriting.
- Keep explicit target-company bootstrap present but disabled by default.
- Preserve auditability through per-round rescue artifacts.
- Avoid scattering feature-flag checks through low-level parsing, query planning, and CTS execution.

## Non-Goals

- No open-ended deep research agent.
- No local company knowledge base.
- No hand-maintained company dictionary.
- No static expansion of segment labels such as "AI six dragons", "large companies", "cloud vendors", or "top SaaS companies".
- No curated technical term dictionary.
- No spaCy, Jieba, or heavyweight NLP dependency for first-phase candidate feedback.
- No multi-round candidate feedback loops.
- No writing candidate feedback terms back into requirement truth.
- No fallback provider chains for web discovery.

## Rescue Router

The runtime should choose exactly one rescue lane when stop guidance enters a rescue window, such as `broaden_required` or a low-quality exhausted state where stopping would otherwise happen.

Priority order:

```text
reserve broaden
-> candidate feedback
-> web company discovery
-> anchor-only/basic search
-> allow stop
```

Conceptual routing:

```text
choose_rescue_lane(ctx):
    if has_untried_reserve_family:
        return reserve_broaden

    if candidate_feedback_enabled and feedback_has_seed_resumes and not candidate_feedback_attempted:
        return candidate_feedback

    if company_discovery_enabled and web_discovery_is_useful and not company_discovery_attempted:
        return web_company_discovery

    if not anchor_only_broaden_attempted:
        return anchor_only

    return allow_stop
```

The router belongs in runtime orchestration. Lower-level modules should not inspect feature flags. They should expose plain functions that receive explicit inputs and return explicit outputs.

## Lane 1: Reserve Broaden

This keeps the current main behavior as the cheapest and safest first rescue.

Trigger:

```text
rescue window is active
and an admitted non-anchor family remains untried
```

Behavior:

```text
anchor + untried reserve term
```

The runtime should mark the round as:

```text
rescue_lane = "reserve_broaden"
```

## Lane 2: Candidate Feedback

Candidate feedback is a guarded relevance-feedback query expansion from already scored fit resumes. It uses current resume-library evidence to discover high-probability surface terms that were missing from the original query term pool.

Trigger:

```text
candidate_feedback_enabled
and not candidate_feedback_attempted
and no untried reserve family remains
and at least two feedback seed resumes exist
and anchor-only has not already been attempted
```

### Feedback Seed Resumes

Use the term `feedback seed resumes` in code and artifacts, not "elite resumes".

A resume can seed feedback only if its current scorecard satisfies:

```text
fit_bucket == "fit"
overall_score >= 75
must_have_match_score >= 70
risk_score <= 45
```

Selection:

```text
min_seed_count = 2
max_seed_count = 5
```

If only one seed resume is available, skip candidate feedback. With two seed resumes, an accepted term must be supported by both. With three to five seed resumes, a term must be supported by at least two, preferably three.

### Extraction Sources

Do not extract from full raw resume text by default. Prefer structured and scored evidence:

1. scorecard `matched_must_haves`
2. scorecard `strengths`
3. scorecard `evidence`
4. scorecard `reasoning_summary`
5. structured skills
6. recent project names and summaries
7. current or recent title
8. recent work experience summaries

Raw resume text may be used only as a bounded fallback when structured fields are insufficient, and only after truncation.

### Candidate Generation

First-phase candidate generation should be deterministic and surface-preserving.

Do not use a curated technology dictionary. Do not hardcode specific good terms such as `LangChain`, `Flink CDC`, or `ClickHouse`.

Use shape-based extraction rules that preserve searchable surface forms:

- uppercase acronyms and acronym phrases;
- tokens with technical symbols such as `+`, `#`, `.`, and `-`;
- CamelCase and mixed-case tokens;
- short English phrases;
- mixed English/acronym phrases;
- short Chinese technical phrases only when they come from structured phrase-like fields or scored evidence.

The rules identify forms that look like searchable technical spans. They do not decide that a term is a known framework or a good query term.

Chinese free n-gram generation is out of scope for the first version.

### Generic and Filter-Like Blocking

A small generic/filter blacklist is allowed because it is a safety rule, not a knowledge base.

Block terms that are generic, filter-like, or likely to cause topic drift:

- generic work words: platform, system, project, development, responsible for, familiar with, business, management, optimization, architecture, experience, ability;
- title-only terms and title-anchor variants;
- company names;
- school names;
- locations;
- degree, age, gender, salary, and years of experience;
- already-tried query terms or same-family terms.

The exact blacklist should stay small and boring. It is a guardrail, not a domain ontology.

### LLM Role

The LLM must not invent feedback terms. It can only classify and rank deterministic candidate terms.

Input to the model:

- job title and compact requirement summary;
- existing query terms and families;
- selected feedback seed snippets;
- deterministic candidate terms.

Output:

- ranked candidates selected only from the provided list;
- support resume ids;
- linked requirement;
- risk flags;
- rejection reasons for unsafe terms.

The runtime must re-check all hard constraints after model output. If all terms are filtered, skip candidate feedback and move to the next rescue lane.

### Scoring

Use an explainable score rather than a model-only decision:

```text
score =
  support_score
  + requirement_score
  + field_score
  + novelty_score
  - risk_penalties
```

Suggested components:

```text
support_score = 4 * support_seed_count

requirement_score =
  3.0 if linked to must-have
  1.5 if linked to core preference
  0.0 otherwise

field_score =
  +2.0 if appears in matched_must_haves or evidence
  +1.5 if appears in skills
  +1.0 if appears in recent project or recent experience
  +0.5 if appears only in reasoning_summary

novelty_score =
  +2.0 if not in query pool and not same family
  -5.0 if already tried or same family

risk_penalties =
  -5.0 for company, school, location, or filter-like terms
  -4.0 for generic terms
  -3.0 for title-anchor variants
  -3.0 when the term is common in not-fit candidates
  -2.0 when the term is too broad
```

Use recent experience as stronger evidence when dates are available. If dates are missing, do not fail the term only for missing recency.

### Negative Feedback

Use recent not-fit and high-risk candidates as negative evidence.

First version can use a simple support-rate difference:

```text
discriminative_score = fit_support_rate - not_fit_support_rate
```

If fewer than three not-fit candidates are available, skip negative-rate penalty or use simple smoothing. Do not let a tiny negative sample suppress an otherwise well-supported feedback term.

### Query Use

Candidate feedback is one-shot:

```text
anchor + one feedback term
```

Do not use multiple feedback terms in one query. Do not run feedback-only queries. Do not run a second candidate-feedback expansion from the results of the first feedback round.

Injected query term shape:

```text
source = "candidate_feedback"
category = "expansion"
retrieval_role = "core_skill"
queryability = "admitted"
family = "feedback.<slug>"
active = true
first_added_round = round_no
```

## Lane 3: Web Company Discovery

Web company discovery is external market mapping. It should run after reserve broaden and candidate feedback are unavailable or already attempted.

Trigger:

```text
company_discovery_enabled
and not company_discovery_attempted
and no untried reserve family remains
and candidate feedback is unavailable or already attempted
and top pool is empty/weak or repeated low-gain behavior is evident
and rounds_remaining >= 2
```

Behavior:

```text
build redacted discovery input
-> Bocha web search
-> Bocha rerank
-> bounded page reads
-> Qwen3.5-Flash evidence extraction
-> evidence-based reducer
-> inject accepted concrete companies
-> force one company seed query
```

JD and notes can provide low-trust source hints, but those hints do not directly become query terms. Segment labels and recruiter shorthand are not accepted companies.

Only concrete companies supported by web evidence can enter the query term pool.

Injected company terms should remain sourcing strategy terms, not requirement truth.

## Explicit Target Company Bootstrap

Keep explicit target-company bootstrap code available, but disable it by default:

```env
SEEKTALENT_TARGET_COMPANY_ENABLED=false
```

This avoids direct query pollution from ambiguous notes. Later work can design a dedicated data-cleaning strategy for explicit target companies, client companies, excluded companies, aliases, and segment labels.

No local company dictionary or static segment expansion should be introduced in this phase.

## Anchor-Only / Basic Search

Anchor-only search remains the final fallback.

Trigger:

```text
no untried reserve family remains
and candidate feedback is unavailable or already attempted/failed
and web discovery is disabled, unavailable, already attempted, or produced no accepted companies
and anchor-only has not already been attempted
```

Behavior:

```text
anchor only
```

If anchor-only fails to improve recall or quality, stopping with a low-quality exhausted reason is allowed.

## State

Keep runtime state small:

```text
candidate_feedback_attempted: bool
company_discovery_attempted: bool
anchor_only_broaden_attempted: bool
rescue_lane_history: list
target_company_plan: dict | None
```

Do not add a large state machine. Most analysis should come from artifacts.

## Artifacts

Every rescue decision should write:

```text
rounds/round_XX/rescue_decision.json
```

Suggested fields:

```json
{
  "trigger_status": "broaden_required",
  "selected_lane": "candidate_feedback",
  "skipped_lanes": [
    {"lane": "reserve_broaden", "reason": "no_untried_reserve_family"}
  ],
  "forced_query_terms": ["AI Agent", "LangGraph"]
}
```

Candidate feedback artifacts:

```text
rounds/round_XX/candidate_feedback_input.json
rounds/round_XX/candidate_feedback_terms.json
rounds/round_XX/candidate_feedback_decision.json
```

`candidate_feedback_terms.json` should include:

- seed resume ids;
- existing query terms and families;
- deterministic candidate terms;
- model-ranked terms;
- filtered terms with reasons;
- accepted term;
- supporting resume ids;
- linked requirements;
- fit and not-fit support rates;
- final score and risk flags.

Web discovery artifacts:

```text
rounds/round_XX/company_discovery_input.json
rounds/round_XX/company_search_queries.json
rounds/round_XX/company_search_results.json
rounds/round_XX/company_search_rerank.json
rounds/round_XX/company_page_reads.json
rounds/round_XX/company_evidence_cards.json
rounds/round_XX/company_discovery_plan.json
```

## TUI Trace

The TUI should display executed rescue lanes, not every skipped lane.

Examples:

```text
Recall repair: reserve broaden with AI Agent + RAG.
Recall repair: extracted feedback term LangGraph from 3 fit seed resumes.
Target company discovery: found 118 pages, reranked 8, read 6, accepted 5 companies.
Recall repair: final basic search with AI Agent.
```

Skipped lane reasons belong in artifacts unless they are directly useful to the user.

## Evaluation

Evaluate rescue lanes by incremental benefit after the lane executes. Do not count candidates already present in the top pool as rescue gains.

Metrics:

```text
rescue_lane
unique_new_count_after_lane
fit_count_after_lane
strong_fit_count_after_lane
new_top10_fit_count
new_top10_strong_fit_count
not_fit_ratio_after_lane
avg_score_after_lane
extra_rounds
extra_cts_calls
extra_llm_calls
web_search_calls
latency
```

Success criteria for low-recall samples:

- fit@10 or strong_fit@10 improves;
- not-fit ratio does not materially increase;
- extra cost and latency remain acceptable;
- topic-drift cases are explainable from artifacts;
- each rescue lane can be disabled independently through high-level flags.

## Merge Guidance

The target-company branch should be merged only after routing changes are aligned with this design.

Merge:

- Bocha provider and rerank;
- bounded page reader;
- web discovery service;
- model steps;
- runtime progress and artifacts;
- TUI trace rendering;
- env/example config.

Adjust before default use:

- `SEEKTALENT_TARGET_COMPANY_ENABLED=false`;
- `SEEKTALENT_COMPANY_DISCOVERY_ENABLED=true`;
- web discovery runs as the third rescue lane, not before candidate feedback;
- explicit target-company bootstrap does not participate in the default early lane;
- segment hints never directly become query terms.

Keep the main anchor-only behavior, but move it behind candidate feedback and web discovery in the router.

## Acceptance Criteria

1. When a rescue window opens and an untried reserve family exists, runtime chooses reserve broaden.
2. When no reserve family remains and at least two feedback seed resumes exist, runtime chooses candidate feedback before web discovery.
3. Candidate feedback injects at most one term and runs exactly one `anchor + feedback_term` query.
4. Candidate feedback does not use spaCy, Jieba, a curated technical dictionary, or a local knowledge base.
5. Candidate feedback model output cannot introduce terms outside the deterministic candidate list.
6. Candidate feedback terms never update requirement truth.
7. When candidate feedback is unavailable or already attempted, web discovery can run if enabled and useful.
8. Web discovery accepts only concrete companies supported by evidence.
9. Segment labels and recruiter shorthand never directly become query terms.
10. Anchor-only search runs only after reserve broaden, candidate feedback, and web discovery are unavailable or exhausted.
11. Each rescue lane is attempted at most once per run.
12. `rescue_decision.json` explains selected and skipped lanes.
13. TUI shows the executed rescue lane in a concise trace.
14. `.env.example` exposes candidate feedback, explicit target-company bootstrap, and web company discovery flags with the chosen defaults.
