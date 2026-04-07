# SeekTalent v0.3 设计文档

## 0. 文档信息

- 版本：`v0.3`
- 状态：`design / proposed`
- 文档目标：为 `Grounded Frontier Runtime` 提供单一高层主契约，并把 canonical 命名统一成可直接服务未来代码的 verbose 风格。
- 文档语言约定：正文使用中文，关键术语保留英文，例如 `GenerateGroundingOutput`、`FrontierState_t`、`SearchControllerDecision_t`、`SearchExecutionPlan_t`、`SearchRunResult`。
- 命名约束：`payloads/` 与 `operators/` 中出现的名字是正式 canonical 名；高层文档不得再引入第二套对象语言。
- 职责说明：本文只定义原则、ownership、命名规则和高层行为。字段级定义以 `payloads/`、`operators/`、[[expansion-trace]] 为准。
- 现状声明：本文描述的是 `v0.3` 目标契约，不代表当前 `HEAD` 已实现。

## 1. 设计结论摘要

`SeekTalent v0.3 = Grounded Frontier Runtime`。

核心变化只有四个：

1. 搜索控制权回到 runtime，由 `SelectActiveFrontierNode` 决定当前扩展哪条 branch。
2. 控制器只负责产出 `SearchControllerDecision_t`，不再自由重写整轮 query。
3. 首轮启动由 `GenerateGroundingOutput` 提供结构化 grounding，而不是靠裸 `JD + notes` 词面硬拉。
4. reflection 不再只是散文建议，而是变成 `BranchEvaluation_t`，可被 `ComputeNodeRewardBreakdown` 和 `EvaluateStopCondition` 直接消费。

## 2. 不变边界

以下事情在 `v0.3` 中不变：

- 原始业务输入仍然只有 `SearchInputTruth` 中的 `job_description + hiring_notes`
- 招聘检索仍然是强结构化、强审计、强约束的垂直系统
- runtime 继续拥有预算、停止、审计与状态回写权
- `CTS` backend / adapter 不是本轮主线重写对象

## 3. Ownership

### 3.1 哪份文档说了算

- 总体原则、命名规则、owner 边界：本文
- 流程解释：[[workflow-explained]]
- payload 对象定义：`payloads/`
- operator 输入输出、白盒变换公式与 read/write set：`operators/`
- 单次扩展 worked example：[[expansion-trace]]
- 评估口径：[[evaluation]]
- 实施顺序与阶段 gate：[[implementation-checklist]]

### 3.2 哪个层负责什么

- `GenerateGroundingOutput` 负责首轮语义启动，不负责 run 期状态控制
- `SelectActiveFrontierNode` 负责选点与上下文打包
- `GenerateSearchControllerDecision` 负责 branch-level operator patch
- `MaterializeSearchExecutionPlan` 负责把 patch 物化为可执行计划
- `EvaluateBranchOutcome` 负责 branch 价值判断
- `ComputeNodeRewardBreakdown` 负责 deterministic reward
- `UpdateFrontierState` 负责 frontier 状态推进
- `EvaluateStopCondition` 负责统一 stop guard
- `FinalizeSearchRun` 负责基于 run-global shortlist 产出最终总结

## 4. 运行时主链

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
- 禁止把 `F_t / d_t / p_t` 这类数学记号当成正式 note 名或对象 owner 名
- 允许并鼓励在公式与状态表示中使用数学记号

### 5.2 全局 Notation Legend

```text
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
- 公式优先使用 `R / P / F_t / n_t / d_t / p_t / x_t / y_t / a_t / b_t`
- operator 卡片中的公式必须写成白盒变换，至少显式展示：
  - 输入投影或 prompt packing
  - 中间量
  - 如果有 LLM，则展示 draft
  - deterministic normalization / clamp / whitelist / merge
  - 最终写入对象
- 禁止把公式写成“对象名 = 动词函数(对象名...)”的黑盒缩写
- 如果某个状态变换更适合集合式表达，优先写 `T(F_{t+1}) = T(F_t) ∪ {...}` 这类式子，而不是长英文函数调用

### 5.4 白盒公式 owner

- `operators/` 是 operator 白盒变换的唯一 owner
- [[expansion-trace]] 是单轮 worked example 的唯一 owner
- `payloads/` 只定义对象 shape / invariants / direct producer / consumer
- `workflow-explained.md`、`operator-map.md`、`evaluation.md`、`implementation-checklist.md` 不重复持有白盒公式

## 6. 高层对象说明

### 6.1 `FrontierState_t / FrontierState_t1`

它们是 run 级状态对象，不是某个 prompt 的私有 memory。

`FrontierState_t` 关心的是：

- 当前有哪些 open node
- run-global shortlist 是什么
- 语义去重表是什么
- 预算还剩多少

上一轮的 `FrontierState_t1` 会在进入下一轮前由 runtime round shift 重绑定为新的 `FrontierState_t`；这不是额外 operator，只是轮次 bookkeeping。

### 6.2 `SearchControllerContext_t`

它是 runtime 选点之后一次性打包出的只读快照，只服务当前 active branch。

### 6.3 `SearchControllerDecision_t`

它是 operator-centered 决策对象，不是自由 query 文本。`stop` 只是 `action` 的一种取值，不再额外发明第二类 stop 对象。

### 6.4 `SearchExecutionPlan_t`

它是检索执行层的唯一计划对象。`target_new_candidate_count` 与 `semantic_hash` 在这里固定，不再分散在外部活体状态里。

### 6.5 `BranchEvaluation_t` 与 `NodeRewardBreakdown_t`

`BranchEvaluation_t` 负责表达 branch judgment，`NodeRewardBreakdown_t` 负责表达 deterministic reward。两者职责分开，避免“反思建议”和“值函数”重新混在一起。

### 6.6 `SearchRunResult`

最终输出受 `FrontierState_t1.run_shortlist_candidate_ids` 事实基础约束。总结文本可以由 LLM 生成，但不能改写 shortlist 事实。

## 7. Grounding 层说明

`GenerateGroundingOutput` 的目标不是 generic `RAG`，而是产出两类结构化对象：

- `GroundingEvidenceCard`
- `FrontierSeedSpecification`

它们服务于 round-0 frontier 初始化与少量 repair，不承担 run 中的全局知识检索。

## 8. Node Reward 与 Stop Guard

`v0.3` 的 stop 不再是某个 prompt 想停就停，而是由 runtime 统一 guard：

- 预算耗尽
- 没有 open node
- 当前 branch 已枯竭且低增益
- 控制器建议 stop 且通过 runtime guard

对应地，reward 也必须拆成可审计的 deterministic breakdown，而不是只留一段自然语言解释。
