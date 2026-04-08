# Business Trace: case-stop-controller-direct-rejected

## 场景背景

- 配对技术版本：[[trace-agent-case-stop-controller-direct-rejected]]
- 岗位目标：控制器想提前结束搜索，但当前轮次还偏早。
- 本 case 关注的问题：系统会不会因为控制器一句“够了”就过早停机。

## 系统路线选择

- 系统没有接受这次 direct-stop，而是要求继续。
- 原因是：当前只到第 1 轮，还没有达到允许 direct-stop 的最小轮次。

## 逐步处理记录

### 1. 当前分支选择（SelectActiveFrontierNode）

- 系统拿到了什么：仍然开放的分支和当前 shortlist。
- 调用了什么工具/服务：运行时优先级打分和 donor 打包逻辑。
- 产出了什么：系统选出当前最值得看的分支 `child_search_domain_01`。
- 对业务意味着什么：即使控制器后面想停，系统依然先按标准流程准备判断上下文。

### 2. 控制器决策（GenerateSearchControllerDecision）

- 系统拿到了什么：当前活跃分支和 run 级状态。
- 调用了什么工具/服务：控制器决策模型（SearchControllerDecisionLLM）和运行时规范化逻辑。
- 产出了什么：控制器建议 `stop`，认为当前 shortlist 已经不错。
- 对业务意味着什么：控制器会表达“是否还值得继续”的主观看法，但这不是最终裁决。

### 3. 前沿状态原样带入（CarryForwardFrontierState）

- 系统拿到了什么：当前完整前沿状态。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：一份用于 stop guard 判定的状态快照，没有新建分支，也没有发起搜索。
- 对业务意味着什么：系统把“停机判断”和“继续搜索”分成了两个明确步骤。

### 4. 停止判断（EvaluateStopCondition）

- 系统拿到了什么：控制器 stop 建议、当前轮次和前沿状态；这里仍没有分支评估和 reward 输入。
- 调用了什么工具/服务：运行时 stop guard。
- 产出了什么：系统拒绝停止，结果是 `continue_flag = true`。
- 对业务意味着什么：这次不允许过早收手，系统会继续下一轮探索。

## 最终结果

- run 没有结束。
- 这条路径的终点是“停止建议被驳回，继续搜索”，而不是产出最终 shortlist。

## 业务解读与风险

- 这条规则可以防止系统因为早期偶然命中几个候选就过早结束。
- 风险点在于：如果最小停机轮次设置得过高，可能会增加一些本可避免的搜索成本。
