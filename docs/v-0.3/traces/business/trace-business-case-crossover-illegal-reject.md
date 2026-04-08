# Business Trace: case-crossover-illegal-reject

## 场景背景

- 配对技术版本：[[trace-agent-case-crossover-illegal-reject]]
- 岗位目标：尝试把 Agent 主线和 retrieval 主线合并。
- 本 case 关注的问题：当控制器想做 crossover，但没有给出必要的共同锚点时，系统能否当场拒绝，而不是放任执行。

## 系统路线选择

- 系统收到的是“尝试 crossover”的建议，但最终没有执行。
- 原因是：虽然 donor 本身是合法候选，但控制器没有给出共享锚点，所以这次交叉不满足物化条件。

## 逐步处理记录

### 1. 当前分支选择（SelectActiveFrontierNode）

- 系统拿到了什么：当前开放的几个分支和它们的历史表现。
- 调用了什么工具/服务：运行时优先级打分和 donor 打包逻辑。
- 产出了什么：系统选中 `child_agent_core_01` 为当前主分支，同时确认 `child_search_domain_01` 是一个合法 donor 候选。
- 对业务意味着什么：这说明 donor 候选本身没有问题，后面的失败不是因为 donor 不合法。

### 2. 控制器决策（GenerateSearchControllerDecision）

- 系统拿到了什么：主分支、donor 候选和未满足要求。
- 调用了什么工具/服务：控制器决策模型（SearchControllerDecisionLLM）和运行时规范化逻辑。
- 产出了什么：控制器请求 `crossover_compose`，但没有给出共享锚点，只保留了 donor 词。
- 对业务意味着什么：这相当于系统提出“想借 donor 的词”，但没有解释两条路线靠什么黏在一起。

### 3. 检索计划物化（MaterializeSearchExecutionPlan）

- 系统拿到了什么：控制器给出的 crossover 参数。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：没有生成任何搜索计划，直接报出 `crossover_requires_shared_anchor`。
- 对业务意味着什么：系统在真正发起搜索前就把这次错误交叉拦住了，不会浪费搜索预算。

## 最终结果

- 这次 crossover 被拒绝，没有执行 CTS 搜索，也没有产生新的 child 分支。
- 终点是“物化失败并返回控制循环”，不是“搜索结果不好”。

## 业务解读与风险

- 这条保护规则的业务意义很强：只有存在共同语义锚点的两条路线才允许合并。
- 如果业务确实希望这两条路线交叉，需要先补出明确的共同锚点，而不是只给 donor 新词。
