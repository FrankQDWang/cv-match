# SeekTalent v0.3 设计文档

## 0. 文档信息

- 版本：`v0.3`
- 状态：`design / proposed`
- 文档目标：为 `Knowledge-Grounded Frontier Runtime` 提供单一高层主契约，并把 canonical 命名统一成可直接服务后续实现的 verbose 风格。
- 文档语言约定：正文使用中文，关键术语保留英文，例如 `RetrieveGroundingKnowledge`、`BusinessPolicyPack`、`ScoringPolicy`、`SearchExecutionPlan_t`、`SearchRunResult`。
- 命名约束：`payloads/` 与 `operators/` 中出现的名字是正式 canonical 名；高层文档不得再引入第二套对象语言。
- 职责说明：本文只定义原则、ownership、命名规则和高层行为。字段级定义以 `payloads/` 与 `operators/` 为准；trace 只持 case replay，不持字段 owner。
- 现状声明：本文描述的是 `v0.3` 目标契约，不代表当前 `HEAD` 已实现。

## 1. 设计结论摘要

`SeekTalent v0.3 = Knowledge-Grounded Frontier Runtime`。

核心变化只有六个：

1. 首轮启动不再裸读 `JD + notes` 造长 query，而是先做 routing-aware grounding retrieval，再生成多个短 seed branches。
2. 评分策略被拆成 `BusinessPolicyPack + RerankerCalibration + ScoringPolicy` 三层，业务偏好与模型校准职责分离。
3. 主排序改为 `reranker + deterministic fusion`，LLM 不再承担主排序职责，只保留解释性输出。
4. bootstrap routing 只有 `explicit_domain / inferred_domain / generic_fallback` 三种模式；generic fallback 不强行贴最近领域。
5. “跳槽频繁”被显式建模为 `CareerStabilityProfile`，默认只做风险 penalty，不下推到检索层。
6. frontier 继续由 runtime 选点，但新增受限的 `crossover_compose`，用于跨分支定向合成新 branch。

## 2. 不变边界

以下事情在 `v0.3` 中不变：

- 原始业务输入仍然只有 `SearchInputTruth` 中的 `job_description + hiring_notes`
- 招聘检索仍然是强结构化、强审计、强约束的垂直系统
- runtime 继续拥有预算、停止、审计与状态回写权
- 运行时知识库只读，不做在线 web search
- `CTS` backend / adapter 不是本轮主线重写对象

## 3. Ownership

### 3.1 哪份文档说了算

- 总体原则、命名规则、owner 边界：本文
- 流程解释：[[workflow-explained]]
- LLM 可见面总览：[[llm-context-surfaces]]
- 权重与阈值索引：[[weights-and-thresholds-index]]
- operator 展示规范：[[operator-spec-style]]
- payload 对象定义：`payloads/`
- operator 输入输出、白盒变换公式与 read/write set：`operators/`
- runtime config / threshold / catalog owner：`runtime/`
- behavior-level helper 语义 owner：`semantics/`
- trace schema 与 case 导航：[[trace-spec]]、[[trace-index]]
- `Agent Trace` case library：`traces/agent/*`
- `Business Trace` case library：`traces/business/*`
- 评估口径：[[evaluation]]
- 实施顺序与阶段 gate：[[implementation-checklist]]
- 知识库与报告编译规则：[[knowledge-base]]
- 真实 CTS 投影与 adapter 继承边界：[[cts-projection-policy]]
- 外部调研提示词：[[deep-research-prompt]]

### 3.2 哪个层负责什么

- `RetrieveGroundingKnowledge` 负责先做领域路由，再从本地知识库中检索与当前岗位最相关的结构化 knowledge cards
- `FreezeScoringPolicy` 负责把 `RequirementSheet + BusinessPolicyPack + RerankerCalibration` 冻结成 run 级评分口径
- `GenerateGroundingOutput` 负责把知识库检索结果和 grounding 草稿归一化成 round-0 可消费的 seed branches
- `SelectActiveFrontierNode` 负责选点与 donor 候选打包
- `GenerateSearchControllerDecision` 负责 branch-level operator patch
- `MaterializeSearchExecutionPlan` 负责把 patch 物化为可执行计划
- `ScoreSearchResults` 负责 `rerank -> calibration -> deterministic fusion -> shortlist`
- `EvaluateBranchOutcome` 负责 branch 价值判断
- `ComputeNodeRewardBreakdown` 负责 deterministic reward
- `UpdateFrontierState` 负责 frontier 状态推进
- `EvaluateStopCondition` 负责统一 stop guard
- `FinalizeSearchRun` 负责基于 run-global shortlist 产出最终总结

### 3.3 LLM Structured Output Contract

`v0.3` 沿用当前仓库 / `v0.2` 的结构化输出基线，不另起新机制。

- 5 个 LLM 调用点都必须使用 provider-native structured output，且要求 strict schema。
- 固定 `retries=0`、`output_retries=1`。
- 不允许退回 prompted JSON、自由文本解析、tool fallback 或 fallback model chain。
- 每个调用点都必须先写入一个 draft payload，再由对应 operator 做 deterministic normalization。
- 只有 schema 之外的真实业务约束，才允许 bounded `output_validator + ModelRetry`。
- 审计层必须至少保留 `output_mode / retries / output_retries / validator_retry_count`。

## 4. 运行时主链

run bootstrap 的主链固定为：

1. `ExtractRequirements`
2. `RetrieveGroundingKnowledge`
3. `FreezeScoringPolicy`
4. `GenerateGroundingOutput`
5. `InitializeFrontierState`

单次 expansion 的主链固定为：

1. `SelectActiveFrontierNode`
2. `GenerateSearchControllerDecision`
3. `MaterializeSearchExecutionPlan`
4. `ExecuteSearchPlan`
5. `ScoreSearchResults`
6. `EvaluateBranchOutcome`
7. `ComputeNodeRewardBreakdown`
8. `UpdateFrontierState`
9. `EvaluateStopCondition`

整次 run 结束时，runtime 用 `RequirementSheet + FrontierState_t1 + stop_reason` 驱动 `FinalizeSearchRun`，产出 `SearchRunResult`。

## 5. Canonical 名与数学记号

### 5.1 分层规则

- verbose canonical 名服务文件名、标题、链接、对象 owner、字段定义和代码基线
- 数学记号服务公式、状态转移、trace 推导和阅读压缩
- 两层必须一一映射，不能互相竞争
- 禁止把 `R / P / F_t` 这类数学记号当成正式 note 名或对象 owner 名
- 允许并鼓励在公式与状态表示中使用数学记号

### 5.2 全局 Notation Legend

```text
B := BusinessPolicyPack
KB := GroundingKnowledgeBaseSnapshot
K := KnowledgeRetrievalResult
C := RerankerCalibration
R := RequirementSheet
P := ScoringPolicy
F_t := FrontierState_t
F_{t+1} := FrontierState_t1
n_t := active frontier node
d_t := SearchControllerDecision_t
p_t := SearchExecutionPlan_t
x_t := SearchExecutionResult_t
y_t := SearchScoringResult_t
a_t := BranchEvaluation_t
b_t := NodeRewardBreakdown_t
```

### 5.3 使用规则

- 图节点、wiki link、章节标题继续使用 verbose canonical 名
- 公式优先使用 `B / KB / K / C / R / P / F_t / n_t / d_t / p_t / x_t / y_t / a_t / b_t`
- operator 卡片中的公式必须写成白盒变换，至少显式展示：
  - 输入投影或 prompt packing
  - 中间量
  - 如果有 LLM，则展示 draft
  - deterministic normalization / clamp / whitelist / merge
  - 最终写入对象
- 禁止把公式写成“对象名 = 动词函数(对象名...)”的黑盒缩写

### 5.4 白盒公式 owner

- `operators/` 是 operator 白盒变换的唯一 owner
- `semantics/` 是 behavior-level helper 的唯一 owner
- `runtime/` 是 runtime config / threshold / catalog 的唯一 owner
- [[trace-spec]] 是 trace taxonomy、模板与 render rule 的唯一 owner
- `traces/agent/*` 是 replay / judge case 的唯一 owner
- `traces/business/*` 是业务复盘 case 的唯一 owner，但事实必须服从 paired `Agent Trace`
- `payloads/` 只定义对象 shape / invariants / direct producer / consumer
- `workflow-explained.md`、`operator-map.md`、`evaluation.md`、`implementation-checklist.md`、`knowledge-base.md` 不重复持有白盒公式

## 6. 高层对象说明

### 6.1 `BusinessPolicyPack`

它表达的是业务偏好，不是需求真相。它可以改变排序偏好、稳定性风险权重、解释口径，但不能回写 `RequirementSheet`。

### 6.2 `GroundingKnowledgeBaseSnapshot` 与 `KnowledgeRetrievalResult`

`GroundingKnowledgeBaseSnapshot` 是运行时只读的知识库快照；`KnowledgeRetrievalResult` 是当前岗位对该快照做 deterministic routing + retrieval 后的局部结果。它除了携带 `retrieved_cards`，还显式携带 `routing_mode / selected_domain_pack_ids / routing_confidence / fallback_reason`。这 4 个 routing fields 由 `KnowledgeRetrievalResult` 直接持有，不再拆出独立 payload。reviewed synthesis reports 保留在 Markdown 中做审核与追溯，但运行时只消费编译后的 knowledge cards。

### 6.3 `ScoringPolicy`

它是 run 级冻结评分口径，持有融合权重、penalty 权重、fit gate、rerank instruction、rerank query text、ranking audit notes 和 calibration snapshot。评分口径一旦冻结，不允许在 branch 扩展中漂移。

### 6.4 `FrontierState_t / FrontierState_t1`

它们是 run 级状态对象，不是某个 prompt 的私有 memory。

其中 `frontier_nodes` 的元素 shape 由 [[FrontierNode_t]] 唯一持有；`FrontierState_t / FrontierState_t1` 只持有 map 容器与 run 级索引。

`FrontierState_t` 关心的是：

- 当前有哪些 open node
- run-global shortlist 是什么
- 语义去重表是什么
- 预算还剩多少
- 每个 node 的 provenance、source card ids 和可选 donor lineage 是什么

### 6.5 `SearchExecutionPlan_t`

它是检索执行层的唯一计划对象。`target_new_candidate_count`、`semantic_hash`、`source_card_ids` 与 `donor_frontier_node_id` 都在这里冻结。

### 6.6 `BranchEvaluation_t` 与 `NodeRewardBreakdown_t`

`BranchEvaluation_t` 负责表达 branch judgment，`NodeRewardBreakdown_t` 负责表达 deterministic reward。两者职责分开，避免“反思建议”和“值函数”重新混在一起。

### 6.7 `SearchRunResult`

最终输出受 `FrontierState_t1.run_shortlist_candidate_ids` 事实基础约束。这个顺序来自 run 内最佳已观测 `fusion_score`，总结文本可以由 LLM 生成，但不能改写 shortlist 事实。

### 6.8 Trace Artifacts

`v0.3` 的 trace 是 dual-view offline artifact，不是 runtime payload。

- `Agent Trace` 服务 replay、judge、实现者审查
- `Business Trace` 服务业务复盘与路线解释
- 两者必须来自同一个 `case_id`，共享同一 operator 顺序与 terminal outcome

## 7. 知识库层说明

`v0.3` 引入的是受限的本地知识库 grounding retrieval，不是通用文档切块检索架构。

知识库设计只有两层：

1. reviewed synthesis reports，保留为 Markdown，用于审核、追溯和编译输入冻结
2. 编译后的 `GroundingKnowledgeCard`，供 runtime 检索和 seed 生成

更底层的多模型原始研究稿只作为 provenance，不再是当前 `v0.3` runtime contract 的正式层。

运行时知识库只服务一件事：

- 在 bootstrap 生成 round-0 seed branches 前，为关键词初始化提供受限的领域上下文

它不承担长期记忆，也不向外部网络扩张。

### 7.1 Routing 与 Generic Fallback

knowledge-grounded bootstrap 的路由只有三种模式：

- `explicit_domain`：业务显式指定 `BusinessPolicyPack.domain_pack_ids`，runtime 直接按给定领域包读取知识卡；不存在的 pack id 直接 fail-fast。
- `inferred_domain`：未显式指定时，runtime 按 `retrieval-semantics` 的 deterministic domain scoring 选择 1-2 个领域包。
- `generic_fallback`：所有领域都没达到阈值时，不强行贴最近领域；`retrieved_cards = []`，`negative_signal_terms = RequirementSheet.exclusion_signals`，并由 `GenerateGroundingOutput` 生成固定顺序的 generic seeds。

generic fallback 不改变主链 owner 分工，只收紧两个边界：

- 不允许 `domain_company` 这类依赖领域知识卡的 operator
- 不允许 LLM 发明领域知识或领域公司线索

### 7.2 Reranker Surface

`v0.3` 中的 `RerankService` 是 text ranking surface，不是生成式 LLM surface。

它只消费三段自然文本：

- `instruction`
- `query`
- `document`

其中：

- `instruction` 是英文任务说明
- `query` 是岗位目标的简洁自然语言表达
- `document` 是候选自然文本表达，不是结构化 JSON dump

如果 runtime 内部持有的是结构化候选对象，必须先在 scoring layer 做 deterministic text conversion，再调用 reranker。

## 8. Node Reward 与 Stop Guard

`v0.3` 的 stop 仍然由 runtime guard 统一裁决：

- 预算耗尽
- 没有 open node
- 当前 branch 已枯竭且低增益
- 控制器建议 stop 且通过 runtime guard

对应地，reward 也必须拆成可审计的 deterministic breakdown。新的 reward 继续消费 novelty / usefulness / diversity / cost，但 top-three 增益改读 fused score，且允许纳入稳定性风险 penalty。
