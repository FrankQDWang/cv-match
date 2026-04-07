# SeekTalent v0.3 实施清单

## 0. 文档定位

本页只定义实施顺序、阶段 gate 与迁移切片，不定义第二套 schema。所有对象名均以 `payloads/` 和 `operators/` 中的 canonical 名为准；数学记号只保留为公式表示层。

## 1. 总体实施顺序

1. `Phase 1`: 文档与命名基线
2. `Phase 2`: frontier runtime 骨架
3. `Phase 3`: round-0 grounding
4. `Phase 4`: branch evaluation + reward + semantic dedupe
5. `Phase 5`: stop / finalize / offline evaluation

## 2. Phase 1: 文档与命名基线

### 2.1 目标

先把 `v0.3` 的 verbose canonical 命名、notation layer 和 owner 边界立住，避免实现仍沿用旧缩写或第二套对象语言。

### 2.2 主要工作

1. 固化 `SearchInputTruth -> ... -> SearchRunResult` 的 payload 主链
2. 固化 `ExtractRequirements -> ... -> FinalizeSearchRun` 的 operator 主链
3. 让 `design.md`、`workflow-explained.md`、`operator-map.md`、`expansion-trace.md` 使用同一套 canonical 名
4. 删除数学缩写和旧对象 alias 的正式 canonical 地位，但保留 `R / P / F_t / d_t ...` 作为公式与 trace 记号
5. 把 `operators/` 卡片统一升级为白盒公式，而不是黑盒函数名

### 2.3 Promotion Gate

1. `docs/v-0.3/` 中不再残留旧的 `v0.2` 对象名
2. 数学记号只出现在公式、notation legend、trace，不再承担正式对象 owner
3. 高层文档不再重复定义字段级 contract
4. `payloads/` 与 `operators/` 已成为唯一 canonical owner
5. `operators/` 已统一采用白盒公式结构

## 3. Phase 2: Frontier Runtime 骨架

### 3.1 目标

搭出 runtime-owned frontier 主链，让 `SelectActiveFrontierNode`、`GenerateSearchControllerDecision`、`MaterializeSearchExecutionPlan`、`UpdateFrontierState` 的 ownership 清晰落地。

### 3.2 主要工作

1. 引入 `FrontierState_t` 与 `FrontierState_t1`
2. 引入 `SearchControllerContext_t` 与 `SearchControllerDecision_t`
3. 引入 `SearchExecutionPlan_t`
4. 明确 run-global shortlist 与 node-local shortlist 的分离

### 3.3 Promotion Gate

1. runtime 已拥有 frontier 选点与状态回写权
2. 控制器只输出 branch-level operator patch
3. 搜索执行层只消费 `SearchExecutionPlan_t`

## 4. Phase 3: Round-0 Grounding

### 4.1 目标

把首轮语义启动从裸词面拼接升级为结构化 grounding。

### 4.2 主要工作

1. 接入 `GenerateGroundingOutput`
2. 让 `InitializeFrontierState` 基于 `GroundingOutput` 启动 frontier
3. 引入 `GroundingEvidenceCard` 与 `FrontierSeedSpecification`
4. 保持 grounding 只服务启动与少量 repair，不扩张为 generic RAG

### 4.3 Promotion Gate

1. 首轮 branch 不再只依赖裸 `JD + notes` 表面词面
2. grounding 与 frontier runtime 职责边界清晰

## 5. Phase 4: Branch Evaluation + Node Reward + Semantic Dedupe

### 5.1 目标

让 branch judgment 能被 deterministic reward 与 stop 直接消费。

### 5.2 主要工作

1. 引入 `BranchEvaluation_t`
2. 引入 `NodeRewardBreakdown_t`
3. 在 `MaterializeSearchExecutionPlan` / `UpdateFrontierState` 中打通 `semantic_hash` 与 dedupe memory
4. 明确 child 节点的 parent baseline snapshot

### 5.3 Promotion Gate

1. `EvaluateBranchOutcome` 与 `ComputeNodeRewardBreakdown` 已职责分离
2. reward breakdown 可审计、可回放
3. semantic dedupe 已进入 frontier 更新主链

## 6. Phase 5: Stop Guard / Search Run Finalization / Evaluation

### 6.1 目标

把 stop guard、最终结果和离线评估闭环补齐。

### 6.2 主要工作

1. 引入 `EvaluateStopCondition`
2. 引入 `FinalizeSearchRun`
3. 用 `SearchRunResult` 收敛最终输出
4. 按 [[evaluation]] 约定准备 offline eval 矩阵

### 6.3 Promotion Gate

1. stop 由 runtime guard 统一裁决
2. `SearchRunResult` 受 run-global shortlist 事实约束
3. 能以统一 artifacts 支撑离线评估与回放

## 7. 文档一致性校验

在进入实现前，先对 `docs/v-0.3/` 做一次固定校验：

1. 正式对象名只有 verbose canonical 名，旧 `v0.2` 对象名为零
2. 数学记号只出现在公式、notation legend、worked example，不出现在正式 note 标题或 owner 定义
3. payload shape / invariants / producer / consumer 只出现在 `payloads/`
4. read/write set 与白盒变换只出现在 `operators/` 与 [[expansion-trace]]
5. `workflow-explained.md`、`operator-map.md`、`evaluation.md`、本页都不重复 payload shape 与 read/write set
6. 任一高层文档里提到的正式对象名，都能在 `payloads/` 或 `operators/` 中找到唯一 owner
