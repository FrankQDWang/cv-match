# Business Trace: case-stop-controller-direct-accepted

## 场景背景

- 配对技术版本：[[trace-agent-case-stop-controller-direct-accepted]]
- 岗位目标：当前 shortlist 已经积累到一个可以交付给业务审核的状态。
- 本 case 关注的问题：控制器直接建议停止时，系统是否会在满足条件后结束 run，而不是强行再搜一轮。

## 系统路线选择

- 系统接受了“direct-stop”建议，并进入最终总结。
- 原因是：当前已经到第 2 轮，满足最小停机轮次要求；同时现有 shortlist 已经足以进入人工复核。

## 逐步处理记录

### 1. 当前分支选择（SelectActiveFrontierNode）

- 系统拿到了什么：仍然开放的几个分支、当前 shortlist 和剩余预算。
- 调用了什么工具/服务：运行时优先级打分和 donor 打包逻辑。
- 产出了什么：系统照常选出当前最值得看的分支 `child_search_domain_01`，即便后面控制器可能会提出停止。
- 对业务意味着什么：停机前，系统依然会把当下语境准备完整，不是“突然终止”。

### 2. 控制器决策（GenerateSearchControllerDecision）

- 系统拿到了什么：当前活跃分支和 run 级状态。
- 调用了什么工具/服务：控制器决策模型（SearchControllerDecisionLLM）和运行时规范化逻辑。
- 产出了什么：控制器建议 `stop`，理由是当前 shortlist 已够强。
- 对业务意味着什么：系统认为继续搜索的边际收益已经不高，可以准备出最终结果。

### 3. 前沿状态原样带入（CarryForwardFrontierState）

- 系统拿到了什么：当前完整的前沿状态。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：一份与当前状态一致的“停机评估输入”，没有创建新子分支，也没有消耗搜索预算。
- 对业务意味着什么：direct-stop 不是假装搜了一轮，而是直接拿现状去做停机判断。

### 4. 停止判断（EvaluateStopCondition）

- 系统拿到了什么：控制器的 stop 建议、当前轮次和前沿状态；这里没有分支评估和 reward 输入。
- 调用了什么工具/服务：运行时 stop guard。
- 产出了什么：系统接受停止，停机原因是 `controller_stop`。
- 对业务意味着什么：控制器有建议权，但最终拍板权仍在运行时守卫；这次建议因为轮次够了，所以被采纳。

### 5. 最终结果生成（FinalizeSearchRun）

- 系统拿到了什么：当前 run 级 shortlist 和停机原因。
- 调用了什么工具/服务：总结模型（SearchRunFinalizationLLM）和运行时确定性逻辑。
- 产出了什么：最终 shortlist 和一段 run 总结。
- 对业务意味着什么：这一步把已有 shortlist 变成可交付的最终输出，但不会改动 shortlist 顺序或停机原因。

## 最终结果

- run 在 direct-stop 路径上正常结束。
- 最终输出是一份按既有排序保留的 shortlist，以及原因明确的 `controller_stop` 停机结论。

## 业务解读与风险

- 这条路径适合“已经搜到足够好结果，不值得继续烧预算”的场景。
- 风险点在于：如果业务偏好更激进地多搜几轮，需要调高最小停机轮次或改变控制器提示策略，而不是靠人工记忆。
