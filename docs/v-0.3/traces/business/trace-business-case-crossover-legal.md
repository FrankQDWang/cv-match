# Business Trace: case-crossover-legal

## 场景背景

- 配对技术版本：[[trace-agent-case-crossover-legal]]
- 岗位目标：在已有 Agent / LLM 主线搜索的基础上，补足 retrieval / ranking 能力。
- 本 case 关注的问题：系统能否合法地把两条已经验证过的分支合并成一条更强的新搜索路线。

## 系统路线选择

- 系统选择了“合法 crossover 扩展”。
- 原因是：当前活跃分支和 donor 分支之间都共享 `rag` 这个共同锚点，而且 donor 分支能补上当前还缺的 `retrieval or ranking experience`。

## 逐步处理记录

### 1. 当前分支选择（SelectActiveFrontierNode）

- 系统拿到了什么：当前还开放的 3 个前沿节点，以及它们过去几轮积累出来的 reward 和 shortlist 表现。
- 调用了什么工具/服务：运行时优先级打分和 donor 打包逻辑。
- 产出了什么：系统选中 `child_agent_core_01` 作为当前主分支，并把 `child_search_domain_01` 打包成唯一 donor 候选，因为两者共享 `rag`，且 donor 有较好的历史收益。
- 对业务意味着什么：系统不是任意拼接两条搜索路线，而是只在“有共同语义锚点、且 donor 确实补短板”时才开放交叉。

### 2. 控制器决策（GenerateSearchControllerDecision）

- 系统拿到了什么：当前主分支、候选 donor 和剩余未覆盖要求。
- 调用了什么工具/服务：控制器决策模型（SearchControllerDecisionLLM）和运行时规范化逻辑。
- 产出了什么：控制器明确请求 `crossover_compose`，保留 `rag` 这个共同锚点，并引入 `retrieval engineer`、`ranking` 两个 donor 词。
- 对业务意味着什么：系统不是简单“多加几个关键词”，而是有意识地在保留主线的同时，引入缺失能力。

### 3. 检索计划物化（MaterializeSearchExecutionPlan）

- 系统拿到了什么：主分支、donor 分支和控制器给出的交叉参数。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：一份可执行搜索计划，查询词收敛为 `rag + retrieval engineer + ranking`，同时保留岗位地点要求和负面过滤条件。
- 对业务意味着什么：到了这一步，交叉想法已经从“策略”变成“能真正执行的搜索计划”，并且 donor 来源被明确记录下来。

### 4. 搜索执行（ExecuteSearchPlan）

- 系统拿到了什么：新的查询词、业务过滤条件和目标拉新数量。
- 调用了什么工具/服务：候选搜索服务（CTS.search）和运行时过滤逻辑。
- 产出了什么：拿回 5 条原始候选记录，去重后保留 4 个候选，并记录了翻页数、重复率、耗时等信息。
- 对业务意味着什么：系统开始验证这条交叉路线能不能找到比旧路线更好的候选人。

### 5. 结果评分（ScoreSearchResults）

- 系统拿到了什么：去重后的候选文本和固定评分口径。
- 调用了什么工具/服务：重排服务（RerankService）和运行时确定性融合逻辑。
- 产出了什么：`c07`、`c19`、`c51` 进入本轮 shortlist，`c77` 因不满足 fit 条件被排除在 shortlist 外。
- 对业务意味着什么：这轮结果不是靠模型拍脑袋排序，而是先做语义重排，再按 must-have、偏好、风险和硬约束统一融合。

### 6. 分支评估（EvaluateBranchOutcome）

- 系统拿到了什么：本轮 shortlist、页面统计和父分支历史表现。
- 调用了什么工具/服务：分支评估模型（BranchOutcomeEvaluationLLM）和运行时规范化逻辑。
- 产出了什么：本轮被判断为有新意、有业务价值，分支未耗尽。
- 对业务意味着什么：系统认为这次交叉不是“换汤不换药”，而是实实在在把缺的能力补进来了。

### 7. 分支收益计算（ComputeNodeRewardBreakdown）

- 系统拿到了什么：父分支 shortlist、本轮 shortlist、run 级 shortlist 和分支评估结果。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：正向 reward，核心收益来自新增 fit 候选、must-have 覆盖改善和 top3 质量提升。
- 对业务意味着什么：系统会把“这次交叉值不值得”量化下来，影响后面是否继续使用类似操作。

### 8. 前沿状态更新（UpdateFrontierState）

- 系统拿到了什么：本轮 child 计划、本轮 shortlist、收益结果。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：父节点关闭，新 child 节点 `child_crossover_03` 加入开放前沿，run 级 shortlist 扩展到 6 人，剩余预算变为 3。
- 对业务意味着什么：这轮扩展不只是得到临时结果，而是真正改写了后续搜索的状态。

### 9. 停止判断（EvaluateStopCondition）

- 系统拿到了什么：更新后的前沿状态、控制器动作和本轮收益。
- 调用了什么工具/服务：运行时 stop guard。
- 产出了什么：系统决定继续，不停止。
- 对业务意味着什么：这条交叉路线表现不错，值得继续探索下一轮。

## 最终结果

- 系统完成了一次合法 crossover，新增了一个带 donor 血缘的 child 分支，并把 shortlist 从原来的 3 人扩展到 6 人。
- 这条 case 最重要的结果是：交叉扩展不只是“允许”，而且确实带来了新增价值。

## 业务解读与风险

- 这条路径适合“当前主分支不错，但还缺一个明确能力块”的情况。
- 风险点在于：如果 donor 的补位价值判断错了，交叉会增加复杂度和成本，所以 donor 的历史 reward 和共享锚点质量很关键。
