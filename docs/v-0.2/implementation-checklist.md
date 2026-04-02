# cv-match v0.2 实施清单

## 0. 文档目的

这份清单把 `design.md` 的设计结论压缩成一份可执行的实施路线。

目标不是重复设计，而是回答下面几个实现问题：

1. 先改什么，后改什么
2. 每一阶段具体动哪些文件
3. 哪些旧概念要保留过渡，哪些要尽快下线
4. 每一阶段完成后，怎样判断可以进入下一阶段

---

## 1. 总体迁移策略

### 1.1 推荐顺序

按下面顺序推进，避免一开始就把 runtime、prompt、UI、tests 一起打散：

1. 先引入新数据模型和状态骨架
2. 再实现 requirement extraction / scoring policy freeze
3. 再实现 query canonicalization / filter projection
4. 再重组 runtime 和 context builder
5. 再切 controller / reflection 契约
6. 最后适配 audit、tests、UI

### 1.2 迁移原则

1. 从 `Phase 2` 开始采用破坏式替换，不再长期保留 `v0.1` / `v0.2` 双契约并存
2. 允许在单个开发中的 commit 里临时不绿，但每个 phase 结束时必须恢复到单一新契约且测试通过
3. 同轮 refill、dedup、normalization、scoring fan-out 这类稳定骨架尽量复用
4. 不在旧 `SearchStrategy`、旧 `CTSQuery`、旧 `ReflectionDecision` 上继续叠语义
5. 一旦新 runtime 主链接上，就立即删除 `soft_filters`、`retrieval_keywords`、旧 prompt 契约

### 1.3 推荐切片

推荐把实现拆成 6 个连续切片：

1. `models + requirement truth`
2. `query planning + filter projection`
3. `runtime + context builder`
4. `controller + reflection`
5. `audit + tests`
6. `cleanup + UI adaptation`

---

## 2. Phase 1: 新模型与状态骨架

### 2.1 目标

把 `v0.2` 的核心契约先立起来，避免后续逻辑继续围绕 `SearchStrategy` 生长。

### 2.2 文件

- `src/cv_match/models.py`
- 可选新增：
  - `src/cv_match/requirements/__init__.py`
  - `src/cv_match/retrieval/__init__.py`

### 2.3 必须新增的模型

在 `models.py` 中新增：

- `InputTruth`
- `RequirementSheet`
- `RequirementDigest`
- `HardConstraintSlots`
- `PreferenceSlots`
- `DegreeRequirement`
- `SchoolTypeRequirement`
- `ExperienceRequirement`
- `GenderRequirement`
- `AgeRequirement`
- `QueryTermCandidate`
- `ReflectionKeywordAdvice`
- `ReflectionFilterAdvice`
- `ReflectionAdvice`
- `RuntimeConstraint`
- `ConstraintProjectionResult`
- `ProposedFilterPlan`
- `RoundRetrievalPlan`
- `SentQueryRecord`
- `RetrievalState`
- `ScoringPolicy`
- `ControllerContext`
- `ReflectionContext`
- `FinalizeContext`
- `RoundState`
- `RunState`

### 2.4 当前状态说明

当前仓库已经先落了一步“并行引入新模型”的脚手架，用来承接后续替换。

如果按“干净的破坏式更新”推进，下一阶段开始应把这批旧模型视为待删除对象，而不是长期兼容层：

- `SearchStrategy`
- `ControllerStateView`
- `ReflectionDecision`
- 旧 `CTSQuery`
- 旧 `ScoringContext`

### 2.5 完成标志

1. `models.py` 能表达 `design.md` 中的核心契约
2. 新模型之间能闭环表达 `InputTruth -> RequirementSheet -> ScoringPolicy -> RunState`
3. 还没改 runtime 也没关系，但类型层已经不再被旧 `SearchStrategy` 卡死

---

## 3. Phase 2: Requirement Extractor 与 ScoringPolicy 冻结

### 3.1 目标

把“需求真相”从检索策略中拆出来。

### 3.2 文件

- 新增 `src/cv_match/requirements/extractor.py`
- 新增 `src/cv_match/requirements/normalization.py`
- 新增 `src/cv_match/prompts/requirements.md`
- 旧 `src/cv_match/controller/strategy_bootstrap.py`
- `src/cv_match/models.py`
- `src/cv_match/config.py`

### 3.3 具体改动

新增 requirement 侧函数：

- `build_input_truth(jd, notes) -> InputTruth`
- `RequirementExtractor.extract(input_truth) -> RequirementSheet`
- `normalize_requirement_draft(draft) -> RequirementSheet`
- `build_requirement_digest(requirement_sheet) -> RequirementDigest`
- `build_scoring_policy(requirement_sheet) -> ScoringPolicy`

抽取与规范化逻辑至少要覆盖：

1. `role_title`
2. `role_summary`
3. `must_have_capabilities`
4. `preferred_capabilities`
5. `exclusion_signals`
6. `hard_constraints`
7. `preferences`
8. `initial_query_term_pool`
9. `scoring_rationale`

实现方式收紧为：

1. `Requirement Extractor` 是显式 LLM 节点
2. LLM 先产出 `RequirementExtractionDraft`
3. `requirements/normalization.py` 只负责 deterministic normalization / canonicalization
4. 不再保留“从原始 `JD + notes` 直接规则生成 `RequirementSheet`”的并行主路径

### 3.4 约束

1. `location` 一旦在 `JD/notes` 中出现，必须进入 `hard_constraints.locations`
2. 学历、院校类型、经验、性别、年龄、公司名都要有标准槽位
3. 槽位允许为空，但“未抽到”和“明确不限”要区分
4. `initial_query_term_pool` 是候选池，不是首轮 CTS query

### 3.5 完成标志

1. runtime 还没切也没关系，但 requirement truth 已可单独生成并落盘
2. scoring policy 可以仅由 `RequirementSheet` 重建
3. 首轮检索不再依赖“把 must_have/preferred 全量拼出来”才能启动
4. `requirements_model`、`prompts/requirements.md`、`RequirementExtractor` 三者已经接入主链

---

## 4. Phase 3: Query Planning 与 Filter Projection

### 4.1 目标

把“controller proposal”与“最终 CTS query”之间的 deterministic runtime 层补出来。

### 4.2 文件

- 新增 `src/cv_match/retrieval/query_plan.py`
- 新增 `src/cv_match/retrieval/filter_projection.py`
- `src/cv_match/clients/cts_client.py`
- `src/cv_match/models.py`

### 4.3 `query_plan.py`

建议提供：

- `normalize_term(term) -> str`
- `canonicalize_controller_query_terms(proposed_terms, round_no) -> list[str]`
- `serialize_keyword_query(terms) -> str`
- `build_round_retrieval_plan(...) -> RoundRetrievalPlan`

必须实现：

1. `budget = round_no + 1`
2. 去空白
3. casefold 去重
4. deterministic serialization
5. term 内含空格时加双引号
6. term 内含双引号时转义
7. budget 不符时 fail-fast

### 4.4 `filter_projection.py`

建议提供：

- `build_default_filter_plan(requirement_sheet) -> ProposedFilterPlan`
- `project_constraints_to_cts(...) -> ConstraintProjectionResult`

必须实现：

1. `location` 不进入 `filter_projection`
2. 其他字段按 `Controller` proposal 投影
3. 不可安全映射到 CTS 的字段进入 `runtime_only_constraints`
4. `adapter_notes` 记录映射成功和失败原因

### 4.5 枚举与 reference data

这一步需要补齐本地 mapping source-of-truth，至少包括：

- `degree`
- `schoolType`
- `workExperienceRange`
- `gender`
- `age`
- `location taxonomy`

如果 reference 文档暂时缺失，先允许：

1. `location` 走 geography taxonomy
2. 其他枚举先保留为 `runtime_only_constraints`
3. 明确在 `adapter_notes` 中记录“未映射，未下发 CTS”

### 4.6 完成标志

1. runtime 已可以从 `proposed_query_terms + proposed_filter_plan` 构建 `RoundRetrievalPlan`
2. `CTSQuery` 只接收 `query_terms + keyword_query + native_filters`
3. 协议层不再出现 `soft_filters`

---

## 5. Phase 4: Runtime 重组为 RunState + Context Builder

### 5.1 目标

把 `orchestrator.py` 从“边跑边拼状态”改成“围绕单一 `RunState` 驱动”。

### 5.2 文件

- `src/cv_match/runtime/orchestrator.py`
- 新增 `src/cv_match/runtime/context_builder.py`
- `src/cv_match/models.py`

### 5.3 `context_builder.py`

建议提供：

- `build_controller_context(run_state) -> ControllerContext`
- `build_scoring_context(run_state, resume_id, round_no) -> ScoringContext`
- `build_reflection_context(run_state, round_state) -> ReflectionContext`
- `build_finalize_context(run_state) -> FinalizeContext`

### 5.4 runtime 具体改动

把 `_run_rounds()` 重组为下面顺序：

1. 构建 `InputTruth`
2. 构建 `RequirementSheet`
3. 冻结 `ScoringPolicy`
4. 初始化 `RetrievalState`
5. 初始化 `RunState`
6. 构建 `ControllerContext`
7. 获取 `ControllerDecision`
8. canonicalize 成 `RoundRetrievalPlan + ConstraintProjectionResult`
9. 由 adapter 生成 `CTSQuery`
10. 执行现有 refill / dedup / normalization / scoring
11. 构建 `ReflectionContext`
12. 获取 `ReflectionAdvice`
13. 更新 `RetrievalState` 和 `round_history`

### 5.5 可复用部分

这些现有逻辑可以尽量原样迁移：

- `_execute_search_tool`
- `_search_once`
- `_dedup_batch`
- `_build_scoring_pool`
- `_normalize_scoring_pool`
- `_build_pool_decisions`

### 5.6 必须删除的旧耦合

1. 不再让 runtime 直接依赖 `bootstrap_search_strategy()`
2. 不再让 `_sanitize_controller_decision()` 通过旧 `build_cts_query_from_strategy()` 偷偷回填最终 query
3. 不再让 scoring context 直接从可变检索策略构造
4. 不再维持新旧 `ControllerDecision` / `CTSQuery` 双 schema 并存

### 5.7 完成标志

1. runtime 有且只有一个在线真相源 `RunState`
2. controller / scoring / reflection / finalize 都通过 context builder 取上下文
3. run 可以完整执行至少一轮，并生成新审计骨架

---

## 6. Phase 5: Controller / Reflection 契约切换

### 6.1 目标

把 LLM 契约从 `v0.1` schema 切换到 `v0.2` schema。

### 6.2 文件

- `src/cv_match/controller/react_controller.py`
- `src/cv_match/reflection/critic.py`
- `src/cv_match/prompts/controller.md`
- `src/cv_match/prompts/reflection.md`
- `src/cv_match/models.py`

### 6.3 Controller 改动

输出从：

- `working_strategy`
- `cts_query`

切换为：

- `proposed_query_terms`
- `proposed_filter_plan`
- `response_to_reflection`

必须保证：

1. controller 看到完整 `JD + notes + RequirementSheet`
2. controller 是 query owner
3. controller 不是最终 CTS protocol owner

### 6.4 Reflection 改动

输入从旧 round summary 升级为完整 `ReflectionContext`。

输出从“直接调整 strategy”切换为：

- `keyword_advice`
- `filter_advice`
- `suggest_stop`
- `stop_reason`
- `reflection_summary`

必须保证：

1. reflection 不再直接改写 runtime state
2. reflection 不再拥有 query final say
3. reflection 必须能看到完整 `JD + notes + RequirementSheet`

### 6.5 prompt 改动

`controller.md` 和 `reflection.md` 都要明确删除旧语义：

- `soft_filters`
- `working_strategy`
- `cts_query` 由 controller 直接生成
- controller / reflection 直接管理 `location` filter
- reflection 只看缩略 round summary

### 6.6 完成标志

1. controller 输出是 proposal，不是 final query
2. reflection 输出是 advice，不是 strategy patch
3. runtime 能解释 controller 是否采纳 reflection 建议

---

## 7. Phase 6: CTS Adapter、Audit、Tests、UI 适配

### 7.1 CTS Adapter

文件：

- `src/cv_match/clients/cts_client.py`
- `src/cv_match/clients/cts_models.py`

改动：

1. `CTSQuery` 改为 `query_terms + keyword_query + native_filters`
2. payload 构建只读取 `native_filters`
3. mock/live 统一移除 `soft_filters` 协议语义
4. 枚举字段的 payload 值由 adapter 负责转换

### 7.2 Audit Store

文件：

- `src/cv_match/runtime/orchestrator.py`
- `src/cv_match/tracing.py`

至少新增落盘：

- `input_truth.json`
- `requirement_sheet.json`
- `scoring_policy.json`
- `sent_query_history.json`
- `rounds/round_xx/retrieval_plan.json`
- `rounds/round_xx/constraint_projection_result.json`
- `rounds/round_xx/controller_decision.json`
- `rounds/round_xx/reflection_context.json`
- `rounds/round_xx/reflection_advice.json`
- `rounds/round_xx/sent_query_records.json`
- `rounds/round_xx/cts_queries.json`

### 7.3 Tests

优先新增或改写：

- `tests/test_requirement_extraction.py`
- `tests/test_query_plan.py`
- `tests/test_filter_projection.py`
- `tests/test_runtime_state_flow.py`
- `tests/test_runtime_audit.py`
- `tests/test_controller_contract.py`
- `tests/test_reflection_contract.py`

必须覆盖：

1. `round_no + 1` budget enforcement
2. query serialization quoting/escaping
3. `location_execution_plan` generation and runtime dispatch
4. unmapped enum -> runtime-only constraint
5. scoring policy frozen across rounds
6. sent query history recorded
7. reflection 只输出 advice

### 7.4 UI 适配

文件：

- `src/cv_match_ui/server.py`
- `src/cv_match_ui/mapper.py`

原则：

1. 尽量保持 API 外观不变
2. UI 不需要理解完整 `RunState`
3. 只在 mapper 层消费新的 final result / audit shape

### 7.5 完成标志

1. `uv run pytest -q` 通过
2. mock 模式能跑通完整多轮流程
3. 审计目录能回答“每轮发了哪些词、为什么换词、哪些约束没下发 CTS”

---

## 8. 旧代码清理清单

按破坏式迁移策略，这些旧概念不应等到项目末尾再清；只要新主链接上，就应尽快删除：

1. `SearchStrategy.retrieval_keywords`
2. `CTSQuery.hard_filters`
3. `CTSQuery.soft_filters`
4. `ScoringContext` 中基于检索策略的可变字段
5. `ReflectionDecision.adjust_*`
6. `ControllerStateView`
7. `build_cts_query_from_strategy()`
8. runtime 中围绕旧 `strategy` 的 sanitize / apply 逻辑

---

## 9. 建议的实际提交顺序

如果按 PR 或 commit 切片，建议顺序如下：

1. `models: add v0.2 truth and planning models`
2. `requirements: add requirement sheet extraction and scoring policy bootstrap`
3. `retrieval: add query planning and filter projection`
4. `runtime: introduce run state and context builder`
5. `controller/reflection: switch to proposal and advice contracts`
6. `cts adapter: switch to native filters and enum projection`
7. `audit/tests: add v0.2 artifacts and coverage`
8. `cleanup: remove v0.1 query/filter semantics`

---

## 10. 阻塞项

当前已知阻塞项只有两个：

1. `design.md` 中引用的枚举参考文档还未落库，枚举字段正式投影前需要先补 source-of-truth
2. 现有 tests 固化了不少 `v0.1` 语义，切 runtime 契约时要接受一轮集中改测

如果这两个阻塞暂时不处理，仍然可以先完成：

1. `RequirementSheet`
2. `ScoringPolicy freeze`
3. query budget enforcement
4. `location_execution_plan`
5. `runtime-only constraint` 主链
