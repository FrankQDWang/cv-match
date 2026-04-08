# grounding-semantics

`GenerateGroundingOutput` 使用的 deterministic helper 语义 owner。

## `select_supporting_cards`

- 非 generic 模式：从 `K.retrieved_cards` 中选择最多 4 张高/中置信度卡，优先覆盖 `R.must_have_capabilities`，再补 `R.preferred_capabilities`
- `generic_fallback`：必须返回空数组

## `normalize_grounding_cards`

- 非 generic 模式：只保留 `source_card_id` 落在 `candidate_support_cards_t` 中的 evidence cards
- 非 generic 模式：`evidence_type` 也必须落在 [[GroundingCatalog]] 中允许的有限集合；非法值直接丢弃
- 草稿为空时，按 supporting cards 自动补一张 evidence card，默认 `evidence_type = title_alias`
- `generic_fallback`：生成 `1-3` 张 `generic_requirement` evidence cards，固定包含 `role_title`，有 must-have 时再补首个与第二个 must-have
- `generic_fallback`：`source_card_id` 必须使用 `generic.requirement.*` 虚拟 id

## `normalize_seed_specifications`

- 非 generic 模式：只接受 `operator_name` 在 [[OperatorCatalog]] 中、且 `source_card_ids` 全部可回溯到 supporting cards 的 seed
- 缺失 `negative_terms` 时，自动补入 `K.negative_signal_terms`
- 缺失 `expected_coverage` 时，按 `source_card_ids` 的 must-have/preferred links 回填
- round-0 seed whitelist 只允许 `must_have_alias / strict_core / domain_company`
- `generic_fallback`：忽略 LLM 草稿，直接合成 deterministic generic seeds

## generic seed synthesis

固定顺序：

1. `role_title_anchor`
   - `operator_name = must_have_alias`
   - `seed_terms = [R.role_title] ∪ title_token_terms ∪ first(R.must_have_capabilities)` 去重后截到 4 个
2. `must_have_core`
   - `operator_name = must_have_alias`
   - `seed_terms = first_two(R.must_have_capabilities) ∪ first(R.preferred_capabilities) ∪ generic_anchor_terms`
3. `coverage_repair`
   - `operator_name = strict_core`
   - `seed_terms = R.must_have_capabilities[2:4] ∪ generic_anchor_terms`
4. 第 4/5 条只在 still-uncovered must-have 存在时生成，每条最多补 1 个剩余 must-have，并复用 `generic_anchor_terms`

generic 模式下不得生成 `domain_company` 或 `crossover_compose`

## `rank_seed_specifications`

排序键固定为：

1. must-have 覆盖数降序
2. preferred 覆盖数降序
3. `selected_domain_pack_ids` 中出现更早的领域优先
4. `seed_rationale` 非空优先

`generic_fallback` 直接保留固定顺序

## `enforce_seed_bounds`

- 总数固定裁到 `3-5` 条
- 每条 `seed_terms` 保序去重后裁到 `2-4` 个
- 语义完全相同的 seed 只保留第一条

## `project_seed_target_location`

- `locations` 恰好只有 1 个时写入该值
- 其他情况写 `null`

## 相关

- [[GenerateGroundingOutput]]
- [[GroundingOutput]]
- [[FrontierSeedSpecification]]
