# Corpus Asset Layer For Benchmark, Search, And Future Resumability Design

## Context

SeekTalent is moving from an experimental local agent toward a production product for recruiters and HR users. Current benchmark inputs are small maintained JD JSONL files under `artifacts/benchmarks/`, and the new flywheel store records query, hit, judge, outcome, term, and query rewriting export assets.

That is not enough for the next phase. Future static benchmarks, a first-party resume search engine, and long-term product learning require a stable corpus layer:

- a JD corpus that can grow from 12 seed JDs to 100+ benchmark-ready tasks;
- a resume corpus that preserves every provider-returned resume snapshot, not only scored or selected candidates;
- provenance that explains which run, query, provider, and stage first surfaced each asset;
- data boundaries that remain compatible with future resumable runs, memory, and cloud multi-tenant isolation.

The user explicitly confirmed:

- ignore old `judge_cache.sqlite3` assets for this rollout;
- default to saving all CTS/provider returned resume snapshots;
- benchmark and query rewriting are separate concepts and must not be coupled;
- resumable execution and personalized memory are not implemented now, but their data boundaries should be anticipated;
- the preferred durable-execution posture is stateless executors with durable DB/artifact ledgers, not a stateful workflow engine as source of truth.

## Goals

1. Add a corpus asset layer for long-term JD and resume accumulation.
2. Save every CTS/provider returned resume snapshot by default.
3. Preserve enough resume text and metadata to build a future first-party search index.
4. Keep corpus, benchmark, and query rewriting flywheel as separate concepts.
5. Add minimal future-facing fields for resumable runs, memory eligibility, sensitivity, tenancy, and provenance.
6. Keep the first implementation small enough to ship before static benchmark and memory features exist.

## Non-Goals

This design does not implement:

- static frozen benchmark pools;
- qrels or benchmark relevance labels;
- a first-party search engine;
- resumable run execution;
- Temporal, LangGraph checkpointing, or another workflow engine;
- personalized memory extraction or prompt injection;
- full cloud IAM, KMS, sandbox orchestration, or tenant provisioning;
- migration of old `judge_cache.sqlite3` assets.

## Architecture Position

Use:

```text
stateless executor + durable DB/artifact ledger
```

Do not use:

```text
stateful graph/workflow runtime as the source of truth
```

LLM calls and agent stages remain stateless. Durable state lives in explicit stores and artifacts. A future scheduler such as Temporal, Celery, or a managed job queue may orchestrate stateless stage execution, but it must not become the canonical owner of business data.

Recovery, when implemented later, should use:

```text
run_id -> stage ledger -> artifact refs -> rebuild context -> continue next stage
```

not:

```text
load Python object / graph checkpoint -> continue hidden in-memory state
```

This is better aligned with a production HR product because assets must be auditable, tenant-scoped, searchable, exportable, and inspectable after a worker exits.

## Storage Boundary

Introduce a new corpus boundary separate from `FlywheelStore`.

```text
.seektalent/
  corpus.sqlite3             # local corpus index and metadata
  flywheel.sqlite3           # query rewriting and run learning data

artifacts/
  corpus/                    # portable corpus exports and manifests
  benchmarks/                # maintained benchmark input JSONL
  benchmark-executions/      # benchmark run execution artifacts
  runs/                      # run trajectory artifacts
  exports/                   # dataset exports, including flywheel exports
```

`CorpusStore` owns long-lived JD and resume documents. `FlywheelStore` owns query rewriting trajectories and derived learning rows. They may reference the same run IDs, query IDs, and resume hashes, but neither store should absorb the other's responsibility.

## CorpusStore Scope

Create a focused `CorpusStore` for:

- JD corpus rows;
- resume document rows;
- provider-returned resume snapshot provenance;
- corpus membership/version rows;
- future-facing metadata needed by benchmark, search, resumability, and memory.

The store should use SQLite locally, with the same discipline as `FlywheelStore`:

- explicit schema version;
- `PRAGMA foreign_keys = ON`;
- WAL mode;
- JSON columns written as canonical JSON and guarded with JSON validity checks where available;
- short transactions;
- no network or artifact file IO inside DB transactions.

## Required Schema

### `jd_documents`

One row per stable JD document.

Fields:

- `jd_doc_id TEXT PRIMARY KEY`
- `tenant_id TEXT NOT NULL`
- `workspace_id TEXT NOT NULL`
- `job_title TEXT NOT NULL`
- `jd_text TEXT NOT NULL`
- `notes_text TEXT NOT NULL`
- `jd_sha256 TEXT NOT NULL`
- `notes_sha256 TEXT NOT NULL`
- `task_sha256 TEXT NOT NULL`
- `language TEXT`
- `domain_tags_json TEXT NOT NULL`
- `seniority TEXT`
- `source_kind TEXT NOT NULL`
- `source_ref TEXT`
- `memory_eligible INTEGER NOT NULL`
- `sensitivity_json TEXT NOT NULL`
- `retention_policy TEXT NOT NULL`
- `schema_version TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

Notes:

- `task_sha256` must include job title, JD text, notes text, and schema version.
- `source_kind` examples: `manual_input`, `benchmark_seed`, `import`, `run_input`.
- `memory_eligible` defaults to `0`.
- `tenant_id` and `workspace_id` are required even in local mode. Local mode may use stable defaults such as `local` / `default`.

### `resume_documents`

One row per stable resume snapshot.

Fields:

- `resume_doc_id TEXT PRIMARY KEY`
- `tenant_id TEXT NOT NULL`
- `workspace_id TEXT NOT NULL`
- `snapshot_sha256 TEXT NOT NULL`
- `source_resume_id TEXT`
- `provider_name TEXT NOT NULL`
- `provider_candidate_id TEXT`
- `dedup_key TEXT`
- `raw_payload_json TEXT NOT NULL`
- `normalized_text TEXT NOT NULL`
- `normalized_sections_json TEXT NOT NULL`
- `skills_json TEXT NOT NULL`
- `experience_json TEXT NOT NULL`
- `education_json TEXT NOT NULL`
- `locations_json TEXT NOT NULL`
- `current_title TEXT`
- `current_company TEXT`
- `searchable_text_version TEXT NOT NULL`
- `normalization_version TEXT NOT NULL`
- `source_kind TEXT NOT NULL`
- `first_seen_run_id TEXT`
- `first_seen_query_instance_id TEXT`
- `first_seen_stage_id TEXT`
- `first_seen_artifact_ref_id TEXT`
- `memory_eligible INTEGER NOT NULL`
- `sensitivity_json TEXT NOT NULL`
- `retention_policy TEXT NOT NULL`
- `schema_version TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

Uniqueness:

- unique within tenant/workspace by `(tenant_id, workspace_id, snapshot_sha256)`;
- `snapshot_sha256` alone is not a global business key across tenants.

Notes:

- The raw payload may contain sensitive candidate data. It is allowed in the local corpus DB for now, but future cloud deployment may move raw payloads to encrypted artifact/blob storage and keep only refs plus searchable extracts in DB.
- `normalized_text` is the future search-engine source text. It should remove obvious transport noise while preserving skills, projects, work summaries, titles, industries, and capability evidence.
- `current_company`, names, salary, school, and location fields may be useful for product display and filtering, but they must be classified in `sensitivity_json`.

### `resume_observations`

One row per provider return event. This preserves the denominator for corpus acquisition and future search evaluation.

Fields:

- `observation_id TEXT PRIMARY KEY`
- `tenant_id TEXT NOT NULL`
- `workspace_id TEXT NOT NULL`
- `resume_doc_id TEXT NOT NULL`
- `run_id TEXT NOT NULL`
- `round_no INTEGER`
- `stage_id TEXT`
- `query_instance_id TEXT`
- `query_fingerprint TEXT`
- `provider_name TEXT NOT NULL`
- `provider_request_id TEXT`
- `provider_rank INTEGER`
- `provider_page_no INTEGER`
- `provider_fetch_no INTEGER`
- `was_scored INTEGER NOT NULL`
- `was_judged INTEGER NOT NULL`
- `was_selected_final INTEGER NOT NULL`
- `source_artifact_ref_id TEXT`
- `created_at TEXT NOT NULL`

Notes:

- Save an observation for every CTS/provider returned resume snapshot by default.
- Scoring and selection flags are metadata on the observation, not a condition for corpus inclusion.
- The same resume may have many observations across runs and queries.

### `corpus_versions`

One row per named corpus version.

Fields:

- `corpus_version_id TEXT PRIMARY KEY`
- `tenant_id TEXT NOT NULL`
- `workspace_id TEXT NOT NULL`
- `name TEXT NOT NULL`
- `description TEXT`
- `builder_version TEXT NOT NULL`
- `builder_config_json TEXT NOT NULL`
- `source_query TEXT NOT NULL`
- `source_run_ids_json TEXT NOT NULL`
- `artifact_ref_id TEXT`
- `row_count INTEGER NOT NULL`
- `created_at TEXT NOT NULL`

First implementation can create only the default growing corpus version, for example `local-default-resume-corpus-v1`.

### `corpus_memberships`

One row per resume document included in a corpus version.

Fields:

- `corpus_version_id TEXT NOT NULL`
- `resume_doc_id TEXT NOT NULL`
- `inclusion_reason TEXT NOT NULL`
- `included_at TEXT NOT NULL`
- primary key `(corpus_version_id, resume_doc_id)`

## Artifact Format

Use `ArtifactStore` logical artifacts for portable corpus materialization.

New artifact kind:

```text
ArtifactKind.CORPUS
collection root: artifacts/corpus/
manifest: manifests/corpus_manifest.json
```

Logical artifacts:

- `corpus.jd_documents`
- `corpus.resume_documents`
- `corpus.resume_observations`
- `corpus.corpus_versions`
- `corpus.corpus_memberships`
- `corpus.export_manifest`

Suggested paths:

```text
corpus/jd_documents.jsonl
corpus/resume_documents.jsonl
corpus/resume_observations.jsonl
corpus/corpus_versions.jsonl
corpus/corpus_memberships.jsonl
corpus/export_manifest.json
```

SQLite is the local queryable index. JSONL artifacts are portable handoff/export assets.

## Runtime Write Path

When retrieval receives provider results:

1. Canonicalize each provider candidate payload.
2. Compute `snapshot_sha256`.
3. Build normalized searchable text and structured sections.
4. Upsert `resume_documents`.
5. Insert `resume_observations` for every provider-returned candidate.
6. Continue existing run logic for dedup, scoring, PRF, top pool, and final selection.

This must happen before scoring filters candidates down. Corpus accumulation should not inherit current scoring/model bias.

When a run starts:

1. Upsert the input JD as a `jd_documents` row.
2. Link run input to the JD doc through existing run/flywheel metadata or a compact run-corpus relation if needed.

The first implementation does not need to populate benchmark pools or qrels.

## Benchmark Boundary

Benchmark and query rewriting are separate products of the asset system.

Benchmark:

- uses JD corpus and future frozen resume pools;
- evaluates product versions;
- eventually owns benchmark sets, pool membership, and qrels.

Query rewriting flywheel:

- uses run/query/hit/outcome/term trajectories;
- exports query rewriting samples;
- does not own benchmark pools or qrels.

Allowed cross-reference:

- `runs.benchmark_id`
- `runs.benchmark_case_id`
- `jd_doc_id`
- `resume_doc_id`
- `snapshot_sha256`
- `query_instance_id`
- `artifact_ref_id`

Forbidden coupling:

- `flywheel-export` must not export benchmark qrels or benchmark reports.
- Corpus accumulation must not depend on eval being enabled.
- Static benchmark rows must not be stored as query rewriting samples.
- Benchmark pool construction must not depend on PRF or generic-explore internals.

## Future Static Benchmark Preparation

Do not implement now, but keep the corpus compatible with future static benchmark tables:

- `benchmark_sets`
- `benchmark_cases`
- `benchmark_case_jds`
- `benchmark_pool_versions`
- `benchmark_pool_members`
- `benchmark_qrels`
- `benchmark_execution_results`

The expected future path:

1. Grow JD corpus to 100+ high-quality cases.
2. Grow resume corpus from all provider returns and later imported/private resume sources.
3. Use multiple retrieval systems to build candidate pools.
4. Freeze pool versions.
5. Generate qrels through judge/human review under explicit contracts.
6. Execute product versions against the frozen benchmark.

## Future Search Engine Preparation

The first-party search engine should build indexes from `resume_documents`, not from run artifacts directly.

The corpus must preserve:

- `normalized_text`
- `normalized_sections_json`
- skill/capability surfaces;
- experience/project summaries;
- seniority/title/location fields;
- source and normalization versions;
- sensitivity markers.

Future index builds should be tracked separately:

- `search_index_build_id`
- `corpus_version_id`
- `index_backend`
- `index_config_hash`
- `index_artifact_ref_id`
- `created_at`

Do not implement index builds in this rollout.

## Future Resumable Run Preparation

This rollout does not implement resumable runs, but corpus rows should carry enough provenance to support a future stage ledger.

The future run-stage ledger should include:

- `run_id`
- `stage_id`
- `stage_type`
- `status`
- `input_hash`
- `output_hash`
- `output_artifact_ref_id`
- `idempotency_key`
- `retry_count`
- `failure_kind`
- `started_at`
- `completed_at`

Corpus fields that align with this:

- `first_seen_run_id`
- `first_seen_query_instance_id`
- `first_seen_stage_id`
- `first_seen_artifact_ref_id`
- `observation_id`
- `source_artifact_ref_id`

If a future run resumes after a crash, it should rebuild context from persisted stage outputs and corpus/flywheel rows. It should not require live process memory.

## Future Memory Preparation

This rollout does not implement personalized memory.

Memory-ready fields are included only to avoid losing provenance:

- `memory_eligible`
- `sensitivity_json`
- `retention_policy`
- `source_kind`
- `source_ref`
- tenant/workspace identifiers.

Rules:

- default `memory_eligible = 0`;
- user explicit feedback may later produce memory-eligible records;
- runtime inference alone should not become long-term user memory by default;
- names, company names, salaries, locations, schools, and contact-like data must be marked sensitive;
- memory extraction must be a separate future design.

## Cloud And Tenant Isolation Preparation

Even local-mode schema must include tenant and workspace scope.

Rules:

- every corpus row includes `tenant_id` and `workspace_id`;
- all query APIs require tenant/workspace filters;
- content hashes such as `snapshot_sha256` are not global authorization keys;
- artifact refs must be tenant-scoped before cloud deployment;
- future sandboxes are execution boundaries, not data ownership boundaries;
- service-managed storage remains the source of truth for recruiter/HR data;
- no cross-tenant corpus, memory, benchmark, or flywheel access is allowed.

First local implementation may use default values:

```text
tenant_id = "local"
workspace_id = "default"
```

but these fields must not be optional.

## Failure Handling

Corpus writes should be best-effort but explicit:

- if corpus write succeeds, continue run normally;
- if corpus write fails because of schema/configuration bugs, fail fast in development/test;
- if provider payload cannot be normalized, save raw payload and record `normalization_failure_kind`;
- do not let a single malformed resume prevent recording other provider results;
- emit corpus write counts and failures into run artifacts.

For production, this may evolve into a stricter policy, but the first version should avoid losing an entire run because one provider candidate is malformed.

## Testing Strategy

Focused tests should cover:

1. Corpus schema creates required tables and enforces JSON validity.
2. JD documents require tenant/workspace and stable hashes.
3. Resume documents are unique by tenant/workspace/snapshot hash.
4. The same snapshot can exist in different tenants without authorization leakage.
5. Retrieval with mock CTS records all provider-returned resumes, not only scored candidates.
6. Resume observations preserve query/run/provider provenance.
7. Corpus accumulation does not require eval.
8. Corpus export writes JSONL through `ArtifactStore` logical names.
9. Flywheel export still contains no benchmark/qrels/corpus-specific output.
10. Static benchmark tables are not implemented in this rollout.
11. Memory fields default to not eligible.
12. Sensitivity metadata is present on JD and resume docs.

## Acceptance Criteria

1. New runs upsert JD input rows into `CorpusStore`.
2. New retrieval results upsert every CTS/provider returned resume snapshot into `CorpusStore`.
3. New retrieval results insert one `resume_observations` row per provider-returned candidate.
4. Corpus rows include tenant/workspace scope.
5. Corpus rows include memory/sensitivity/retention metadata.
6. Corpus assets can be materialized through `ArtifactStore` logical artifacts.
7. `FlywheelStore` remains the query rewriting data boundary and is not renamed or expanded into benchmark/corpus ownership.
8. `flywheel-export` remains query rewriting only.
9. Static benchmark pool/qrels tables are not implemented yet.
10. Resumable run execution is not implemented yet.
11. Personalized memory runtime is not implemented yet.
12. Tests prove corpus accumulation does not require eval.

## Rollout Order

1. Add corpus artifact kind and logical artifact names.
2. Add `CorpusStore` schema and primitive upsert APIs.
3. Add resume normalization/searchable-text helper if no existing helper is clean enough.
4. Wire JD input upsert at run start.
5. Wire all provider-returned resume snapshots and observations at retrieval time.
6. Add corpus export/materialization.
7. Update docs and env defaults.
8. Run focused tests and full suite.

## Open Decisions For Future Specs

These are intentionally not decided here:

- exact static benchmark qrel schema;
- whether qrels are human-only, judge-only, or hybrid;
- search engine backend;
- whether corpus DB remains SQLite in cloud or moves to Postgres plus object storage;
- resumable run stage ledger schema;
- human-in-the-loop intervention flow;
- personalized memory extraction policy.

## Summary

The next implementation should build the corpus asset layer now because it is the shared data foundation for future static benchmark, search, and product learning. It should not implement benchmark pools, qrels, durable execution, or personalized memory yet.

The architectural stance is stateless execution with durable DB/artifact facts. This keeps the system auditable, restartable, and compatible with future cloud tenant isolation without prematurely adopting a stateful workflow engine.
