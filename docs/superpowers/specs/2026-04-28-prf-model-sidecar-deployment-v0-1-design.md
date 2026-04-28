# PRF Model Sidecar Deployment v0.1 Design

Date: 2026-04-28

## Context

`PRF v1.5` now has the right application-side boundary:

- typed proposal artifacts
- exact-offset extractive enforcement
- replayable proposal metadata and version vectors
- shadow vs mainline rollout
- deterministic PRF gate
- legacy fallback

What is still missing is real model serving.

Today, the runtime does not actually load `GLiNER2` or a multilingual embedding model inside the request path. The current orchestrator calls [`build_prf_span_extractor(..., backend=None)`](/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/runtime/orchestrator.py:2136), which intentionally falls back to [`LegacyRegexSpanExtractor`](/Users/frankqdwang/Agents/SeekTalent-0.2.4/src/seektalent/candidate_feedback/proposal_runtime.py:137). Familying also still defaults to exact-surface similarity unless an embedding similarity backend is explicitly supplied.

This is deliberate. The repository first established replayability, artifact identity, shadow/mainline boundaries, and deterministic gate inputs before connecting real local models.

The next step is to deploy real local model inference without breaking those boundaries.

## Goals

- Deploy a real local span-proposal model for `PRF v1.5`.
- Deploy a real local multilingual embedding model for familying similarity.
- Keep all request sandboxes free of direct model imports and direct Hugging Face loading.
- Reuse one local model service across many request sandboxes on the same host.
- Keep model downloads off the request path.
- Pin models by revision and make runtime behavior reproducible.
- Preserve the current `shadow -> mainline` rollout contract.
- Preserve legacy fallback when the sidecar is unavailable or disallowed.

## Non-Goals

- No GPU requirement in Phase 1.
- No per-sandbox model loading.
- No model downloads during an active request.
- No free-form query generation.
- No movement of PRF gate logic into the model service.
- No embedding-driven query generation.
- No knowledge base, alias dictionary, or maintained term lexicon.
- No cross-host distributed inference system in Phase 1.

## Decision Summary

This design makes eight decisions:

1. Run one shared local `PRF model sidecar` per host.
2. Deploy it as a Docker container in CPU-only mode.
3. Let sandboxes access it only through a configured local endpoint contract.
4. Let the sidecar serve both span proposal and embedding inference.
5. Cache model weights in a host-mounted volume keyed by `model + revision`.
6. Keep deterministic alignment, familying guardrails, gating, artifacts, and replay assembly in the main app.
7. Keep runtime fallback to the legacy extractor when dependency gates or sidecar availability fail.
8. Allow `mainline` use only when pinned revisions, dependency gate, and bakeoff promotion criteria are satisfied.

## Why One Shared Sidecar

Three deployment shapes were considered.

### Option A: Per-Sandbox Model Loading

Each request sandbox loads `GLiNER2` and the embedding model locally.

Pros:

- strong process isolation
- no local service dependency

Cons:

- repeated model initialization on every request
- poor CPU-only latency
- repeated memory cost
- repeated model-cache coordination
- mixes model-serving concerns into the sandbox runtime

### Option B: One Shared Local Sidecar

One host-level service loads the models once and serves all request sandboxes on that machine.

Pros:

- best fit for CPU-only Phase 1
- avoids repeated startup cost
- keeps model dependencies out of sandboxes
- clearer replay and dependency boundaries
- naturally compatible with future cloud deployment

Cons:

- shared hotspot under load
- requires local service lifecycle management

### Option C: Separate Sidecars For Span And Embedding

Pros:

- cleaner service boundaries
- easier independent scaling later

Cons:

- more moving parts now
- two service lifecycles
- two health checks
- two failure surfaces

## Recommendation

Choose **Option B** for Phase 1.

This is the smallest deployment step that gives real model inference without collapsing the current productization boundary. It keeps sandboxes small, avoids model downloads during requests, and leaves the deterministic PRF decision logic in the main application where it already belongs.

## Architecture

Phase 1 introduces four runtime roles.

### 1. Request Sandbox

Each workflow request still runs in its own sandbox.

The sandbox:

- may construct PRF proposal inputs
- may call the local sidecar over HTTP
- may perform exact-offset alignment and extractive validation
- may build phrase families
- may run the deterministic PRF gate
- may persist artifacts and replay metadata

The sandbox must not:

- import or initialize `GLiNER2`
- import or initialize the embedding model
- download model weights
- decide its own model revisions

### 2. PRF Model Sidecar

One host-local sidecar serves both:

- span proposal inference
- embedding inference

The sidecar is responsible for:

- loading pinned model revisions
- owning the local model cache
- exposing health and inference endpoints
- enforcing that only configured model/revision pairs are active

The sidecar is not responsible for:

- exact-offset enforcement
- candidate span validation
- family merge policy
- PRF acceptance policy
- provider query construction
- artifact persistence

### 3. Host Model Cache Volume

All model weights are stored in a host-mounted cache volume.

Cache keys must include at least:

- model name
- model revision
- tokenizer revision when applicable

Expected behavior:

- first startup for a new revision downloads once
- subsequent sidecar restarts reuse cached artifacts
- request sandboxes never trigger downloads

### 4. Main Application Adapters

The main application must introduce HTTP-backed implementations of the existing seams instead of inventing a second runtime path.

At minimum:

- `HttpSpanModelBackend`
- `HttpEmbeddingBackend`

These backends plug into the existing proposal runtime boundary rather than bypassing it.

## Deployment Network Contract

The sidecar endpoint is configuration-driven. It must not be hard-coded to `127.0.0.1:8741`.

Phase 1 allows the following deployment shapes:

1. non-container sandbox on the same host as the sidecar
2. Docker sandbox plus Docker sidecar on the same user-defined Docker network
3. explicitly reviewed Linux host-network deployments

Supported examples:

- non-container sandbox: `http://127.0.0.1:8741`
- Docker network service discovery: `http://prf-model-sidecar:8741`

Rules:

- `127.0.0.1` is allowed only when sandbox and sidecar actually share the same host or network namespace
- production sidecar must not bind `0.0.0.0` unless a non-default deployment profile explicitly allows it
- request sandboxes must call a configured sidecar endpoint, not infer one
- the sandbox must not mount the model cache volume directly
- the sandbox must not call external Hugging Face endpoints
- the sidecar may access the model cache volume only during startup, warmup, or explicit cache management

Optional future hardening such as Unix domain sockets is out of scope for Phase 1.

## Model Choices

Phase 1 deployment candidate defaults remain:

- span proposal candidate: `fastino/gliner2-multi-v1`
- embedding candidate: `Alibaba-NLP/gte-multilingual-base`

These remain candidates, not already-proven winners. Bakeoff and shadow evaluation still decide whether the model-backed path is promoted.

The deployment system must support revision pinning for both models and must not assume "latest".

## HTTP API

The sidecar exposes four endpoints.

### `GET /livez`

Purpose:

- simple liveness probe

### `GET /readyz`

Purpose:

- readiness
- model/revision visibility

Response fields must include:

- `status`
- `dependency_manifest_hash`
- `endpoint_contract_version`
- `span_model_loaded`
- `embedding_model_loaded`
- `span_model_name`
- `span_model_revision`
- `span_tokenizer_revision`
- `embedding_model_name`
- `embedding_model_revision`

### `POST /v1/span-extract`

Purpose:

- return raw model span proposals for one or more text slices

Request must include:

- `texts`
- `labels`
- `schema_version`
- `model_name`
- `model_revision`
- `request_id`

Response must include:

- `schema_version`
- `model_name`
- `model_revision`
- `rows`

Each response row must include:

- `request_text_index`
- `surface`
- `label`
- `score`
- `model_start_char`
- `model_end_char`
- `alignment_hint_only`

Important rule:

The sidecar is not trusted to define final offsets. The sidecar may return raw surfaces only. The sandbox remains responsible for deterministic source alignment and exact extractive validation.

### `POST /v1/embed`

Purpose:

- return embeddings for phrase surfaces used in familying

Request must include:

- `phrases`
- `model_name`
- `model_revision`
- `request_id`

Response must include:

- `schema_version`
- `model_name`
- `model_revision`
- `embedding_dimension`
- `normalized`
- `pooling`
- `dtype`
- `max_input_tokens`
- `truncation`
- `vectors`

Phase 1 keeps similarity calculation in the main app so that familying rules, thresholds, and replay artifacts stay transparent and versioned inside the PRF proposal contract.

All inference endpoints must also define:

- maximum batch size
- payload byte limit
- timeout budget
- deterministic response ordering
- structured error schema

## Startup, Warmup, And Offline Mode

The sidecar startup sequence is:

1. read configured model names and pinned revisions
2. verify local cache presence
3. optionally prefetch missing revisions in development bootstrap mode
4. load span model
5. load embedding model
6. expose `ready` health state

The request path must never perform:

- model download
- tokenizer download
- remote code retrieval

If startup cannot satisfy the pinned dependency contract, the sidecar must fail readiness rather than starting in a partially defined state.

Phase 1 distinguishes two execution profiles:

### Development Bootstrap Mode

Allowed behavior:

- may download pinned model snapshots into the host cache
- may be used for first-time local setup and cache warmup

### Production Serve Mode

Required behavior:

- `HF_HUB_OFFLINE=1`
- `local_files_only=True` where supported
- no external model download on startup
- no external network egress required for model resolution
- readiness must fail if the pinned cache is absent or incomplete

Phase 1 therefore requires a separate prefetch or warmup command or job that can populate the host cache before production serving begins.

## Revision And Dependency Gate

The deployment contract must align with the existing PRF dependency gate.

Required for `mainline`:

- non-empty span model revision
- non-empty tokenizer revision
- non-empty embedding model revision
- explicit schema version
- explicit remote-code policy

Phase 1 keeps these rules:

- `shadow` may fall back
- `mainline` must be pinned

No sidecar configuration may silently float to an unpinned model revision.

## Sidecar Dependency Manifest

The sidecar must expose and persist a dependency manifest that is stronger than "model revision only".

At minimum the manifest must capture:

- `sidecar_image_digest`
- `python_lockfile_hash`
- `torch_version`
- `transformers_version`
- `sentence_transformers_version` if used
- `gliner_runtime_version`
- `span_model_name`
- `span_model_commit`
- `span_tokenizer_commit`
- `embedding_model_name`
- `embedding_model_commit`
- `remote_code_policy`
- `remote_code_commit` when applicable
- `license_status`
- `embedding_normalization`
- `embedding_dimension`
- `dtype`
- `max_input_tokens`

The manifest itself may be stored as a separate artifact, but `readyz` and replay metadata must include at least a stable `dependency_manifest_hash`.

## Remote Code Policy

Remote code is treated as a deployment decision, not a request-time flag.

Rules:

- request sandboxes never enable remote code
- sidecar runtime config must not freely toggle remote code per request
- if a model requires custom code, that code path must be reviewed, pinned, and baked into the approved deployment setup

This matters in particular for embedding candidates that may rely on `trust_remote_code=True`.

## Integration With Current PRF v1.5 Runtime

Add one explicit backend selector:

- `prf_model_backend = "legacy" | "http_sidecar"`

Behavior:

- `legacy`: current regex extractor path only
- `http_sidecar`: use HTTP backends for span proposal and embedding similarity when dependency gate allows it

Rollout remains two-stage.

### Shadow Mode

- `prf_v1_5_mode = "shadow"`
- `prf_model_backend = "http_sidecar"`

In shadow mode:

- the sandbox calls the sidecar
- span proposals and familying artifacts are written
- replay snapshot carries sidecar-backed version info
- `SecondLaneDecision.selected_lane_type` must not change because of the new extractor
- shadow sidecar calls must use an independent small timeout budget
- shadow timeout or sidecar failure must not block retrieval
- shadow timeout or sidecar failure must record fallback metadata and continue

### Mainline Mode

- `prf_v1_5_mode = "mainline"`
- `prf_model_backend = "http_sidecar"`

Mainline is allowed only when:

- bakeoff promotion criteria passed
- model dependency gate passed
- sidecar is ready
- revisions are pinned

Then and only then may sidecar-backed proposal outputs drive `prf_probe`.

Mainline timeout is independently configurable from shadow timeout.

## Failure Behavior

Failure handling must stay simple and explicit.

If any of the following happen:

- sidecar unreachable
- sidecar timeout
- sidecar schema mismatch
- sidecar returns malformed response
- configured revision unavailable
- dependency gate fails
- embedding backend unavailable

then the runtime must:

1. record the failure reason
2. mark proposal metadata as legacy fallback
3. use the legacy regex span extractor plus the existing deterministic PRF gate
4. continue the retrieval workflow

This is a fallback to the current known behavior, not a retry storm or alternate model chain.

Important clarification:

- sidecar failure does not imply `generic_explore`
- fallback preserves the legacy PRF path
- the selected lane may still be `prf_probe` if the legacy extractor and existing PRF gate accept a candidate

## Docker Deployment Shape

Phase 1 deployment uses one Docker container for the sidecar.

Recommended runtime characteristics:

- CPU-only
- one container per host
- host-mounted cache volume
- local endpoint binding only under the configured deployment shape

Example logical mounts:

- `/var/lib/seektalent-model-cache` -> sidecar model cache
- configured local endpoint for HTTP only

The sidecar container should be independently restartable from request sandboxes.

## Observability

The sidecar must emit enough metadata for operations, but the main app remains the source of PRF replay truth.

Sidecar observability:

- loaded model names
- loaded revisions
- startup duration
- request counts
- error counts
- request latency buckets

Privacy rules:

- sidecar logs must not include raw request texts by default
- sidecar logs must not include raw resume evidence by default
- sidecar logs must not include raw phrase inputs or embedding payloads by default
- raw-text debug logging requires an explicit local-development flag

Main-app observability and replay:

- proposal artifact refs
- `prf_model_backend`
- `prf_sidecar_endpoint_contract_version`
- `prf_sidecar_dependency_manifest_hash`
- `prf_sidecar_image_digest`
- span model name and revision
- tokenizer revision
- embedding model name and revision
- embedding dimension
- embedding normalization mode
- remote code policy
- familying version and thresholds
- runtime mode
- fallback reason when applicable

## Artifact And Replay Alignment

No sidecar-backed output may bypass `ArtifactStore` or `ArtifactResolver`.

Existing logical artifact names remain the active boundary:

- `round.XX.retrieval.prf_span_candidates`
- `round.XX.retrieval.prf_expression_families`
- `round.XX.retrieval.prf_policy_decision`
- `round.XX.retrieval.second_lane_decision`
- `round.XX.retrieval.replay_snapshot`

New sidecar-related metadata must be attached through the existing typed artifact and replay contract, not by ad hoc files or sidecar-local logs.

## Why Similarity Stays In The Main App

Even with a sidecar, familying logic should stay in the main app because it is not "just inference". It affects:

- support counting
- negative support
- tried-family rejection
- final accepted expression-family selection

That is PRF policy input, not just vector math. The sidecar should supply embeddings; the main app should continue to own family merge semantics.

## Testing Expectations

Phase 1 implementation must cover:

1. sidecar liveness and readiness behavior
2. host-cache reuse across restarts
3. no request-path model downloads
4. sandbox uses configured HTTP endpoint only
5. shadow mode writes sidecar-backed artifacts but does not change lane routing
6. mainline mode requires pinned revisions, dependency manifest, and ready sidecar
7. unreachable sidecar triggers legacy fallback
8. replay snapshot includes sidecar model metadata and manifest hash
9. runtime modules do not directly import model-loading libraries when using sidecar mode
10. request path does not call `from_pretrained`, `snapshot_download`, or equivalent download helpers
11. shadow timeout does not change `SecondLaneDecision.selected_lane_type`
12. sidecar-backed outputs still resolve through logical artifact names

## Acceptance Criteria

The design is considered successfully implemented when all of the following are true:

1. A CPU-only Docker sidecar can load a pinned span model and a pinned embedding model from a host-mounted cache.
2. Request sandboxes can obtain span proposals and embeddings only through the configured local endpoint contract.
3. No request path downloads model artifacts.
4. Production serve mode starts from cache-only or offline state and fails readiness if pinned snapshots are absent.
5. The current PRF v1.5 artifact and replay contract remains intact.
6. Shadow mode produces sidecar-backed proposal artifacts without changing second-lane behavior and stays within the configured shadow latency budget.
7. Mainline mode can use the sidecar-backed extractor only when dependency gates and promotion gates pass.
8. Any sidecar failure cleanly falls back to the legacy extractor path and existing PRF gate.

## Future Follow-Up

This design intentionally stops at single-host local deployment.

Possible later work:

- split span and embedding into separate services if load demands it
- introduce host-level warmup orchestration
- move from localhost-only sidecar to a network service in multi-host cloud deployment
- add model-pool observability for production operations

Those are later optimizations, not Phase 1 requirements.
