# Architecture

`HEAD` uses a versioned model-first documentation system:

- `docs/v-0.3.3/` describes the active runtime and current trace surfaces
- `docs/v-0.3.2/` is the frozen pre-cutover baseline
- `docs/_archive/v-0.3.1/` is historical implementation reference only

## 当前代码主结构

### Contracts

- `src/seektalent/models.py`
- 稳定 runtime payload：`SearchInputTruth`、`RequirementSheet`、`DomainKnowledgePack`、`BootstrapRoutingResult`、`BootstrapOutput`、`SearchExecutionPlan_t`、`SearchExecutionResult_t`、`SearchScoringResult_t`、`SearchRunResult`、`SearchRunBundle`
- frontier runtime state：`FrontierSeedSpecification`、`FrontierNode_t`、`FrontierState_t`

### Bootstrap

- `src/seektalent/bootstrap.py`
- `src/seektalent/bootstrap_ops.py`
- round-0 固定顺序是：
  1. `ExtractRequirements`
  2. `RouteDomainKnowledgePack`
  3. `FreezeScoringPolicy`
  4. `GenerateBootstrapOutput`
  5. `InitializeFrontierState`

### Search / Ranking

- `src/seektalent/search_ops.py`
- `SearchExecutionPlan_t -> SearchExecutionResult_t -> SearchScoringResult_t`
- reranker 只消费 `instruction / query / document-text`

### Runtime loop

- `src/seektalent/runtime/orchestrator.py`
- `run()` / `run_async()` 执行完整 loop，写盘 `bundle.json / final_result.json / eval.json`，返回 `SearchRunBundle`

### Runtime assets

- `artifacts/runtime/active.json`
- `artifacts/knowledge/packs/*.json`
- `artifacts/runtime/policies/*.json`
- `artifacts/runtime/calibrations/*.json`

## 当前明确不再存在的旧层

- runtime card retrieval
- reviewed reports / compiled snapshot 作为运行时输入
- dual-domain bootstrap
- `source_card_ids` provenance
- `KnowledgeRetrievalResult / GroundingDraft / GroundingOutput` 这套旧 bootstrap payload

## Spec ownership

- `docs/v-0.3.3/` 是当前 `HEAD` 的有效 spec 和实现锚点
- `docs/v-0.3.2/` 保留为切换前基线对照
- `docs/_archive/v-0.3.1/`、`docs/_archive/v-0.2/` 和 `docs/_archive/v-0.1/` 只保留归档价值

## Related docs

- [System Model](/Users/frankqdwang/Agents/SeekTalent/docs/v-0.3.3/SYSTEM_MODEL.md)
- [Runtime Sequence](/Users/frankqdwang/Agents/SeekTalent/docs/v-0.3.3/RUNTIME_SEQUENCE.md)
- [Implementation Owners](/Users/frankqdwang/Agents/SeekTalent/docs/v-0.3.3/IMPLEMENTATION_OWNERS.md)
- [Frozen v0.3.2 System Model](/Users/frankqdwang/Agents/SeekTalent/docs/v-0.3.2/SYSTEM_MODEL.md)
- [Configuration](/Users/frankqdwang/Agents/SeekTalent/docs/configuration.md)
- [CLI](/Users/frankqdwang/Agents/SeekTalent/docs/cli.md)
- [Archived Implementation Checklist](/Users/frankqdwang/Agents/SeekTalent/docs/_archive/v-0.3.1/implementation-checklist.md)
