# Business Trace: case-stop-exhausted-low-gain-and-finalize

## 场景背景

- 配对技术版本：[[trace-agent-case-stop-exhausted-low-gain-and-finalize]]
- 岗位目标：系统已经有一份不错的 shortlist，但当前这条分支的追加价值很弱。
- 本 case 关注的问题：当某一轮扩展明显低增益时，系统能否收手并保留已有最好结果。

## 系统路线选择

- 系统选择“低增益停机并 finalize”。
- 原因是：当前分支几乎没有带来新的 fit 候选，收益低于停机阈值，继续搜的性价比很差。

## 逐步处理记录

### 1. 分支评估（EvaluateBranchOutcome）

- 系统拿到了什么：本轮 query、搜索返回、当前 shortlist 和父分支历史表现。
- 调用了什么工具/服务：分支评估模型（BranchOutcomeEvaluationLLM）和运行时规范化逻辑。
- 产出了什么：系统判断这条分支几乎没有新意，业务价值也偏低，并把它标记为“已耗尽”。
- 对业务意味着什么：这不是“结果完全错误”，而是“这条路已经挖不出更多有价值的人了”。

### 2. 分支收益计算（ComputeNodeRewardBreakdown）

- 系统拿到了什么：父分支 shortlist、本轮 shortlist、run 级 shortlist 和分支评估结果。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：本轮 reward 只有 `0.41`，明显低于停机阈值；最主要的问题是没有新增 fit 候选。
- 对业务意味着什么：系统把“这轮没什么收获”量化成一个可比较的结果，而不是只靠主观印象。

### 3. 前沿状态更新（UpdateFrontierState）

- 系统拿到了什么：本轮 child 分支和收益结果。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：父节点关闭，新 child 因已耗尽也不会继续保持开放；run 级 shortlist 保持不变，预算减少到 2。
- 对业务意味着什么：这轮没有把 shortlist 变好，所以系统保留原有最好结果，不因为“搜过一次”就强行改榜单。

### 4. 停止判断（EvaluateStopCondition）

- 系统拿到了什么：更新后的前沿状态、当前分支收益和停机阈值。
- 调用了什么工具/服务：运行时 stop guard。
- 产出了什么：系统给出 `exhausted_low_gain`，决定停止。
- 对业务意味着什么：虽然理论上还有预算、也还有别的开放节点，但 runtime 认为继续搜的价值已经低到不值得。

### 5. 最终结果生成（FinalizeSearchRun）

- 系统拿到了什么：当前 run 级 shortlist 和停机原因。
- 调用了什么工具/服务：总结模型（SearchRunFinalizationLLM）和运行时确定性逻辑。
- 产出了什么：最终 shortlist 沿用已有最好结果，并附上“为什么停在这里”的总结。
- 对业务意味着什么：系统把已有最强 shortlist 作为最终交付，而不是被最后一轮低质量扩展扰动。

## 最终结果

- run 因 `exhausted_low_gain` 停机，并输出最终 shortlist。
- 本轮扩展没有把 shortlist 做得更好，因此最终结果沿用此前累积出的最好候选顺序。

## 业务解读与风险

- 这条路径适合“继续搜索明显边际递减”的场景，能避免为了搜而搜。
- 风险点在于：如果停机阈值设得过激进，可能会提前放弃仍有价值的次优分支，所以阈值治理要和业务预期一起看。
