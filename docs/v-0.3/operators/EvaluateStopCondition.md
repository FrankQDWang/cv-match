# EvaluateStopCondition

统一裁决是否停止，而不是把 stop 决策下放给单个 prompt。

## 公式

```text
budget_exhausted_t = (F_{t+1}.remaining_budget <= 0)
no_open_node_t = (|F_{t+1}.open_frontier_node_ids| = 0)

low_gain_branch_t = (
  a_t.branch_exhausted
  and a_t.novelty_score < stop_guard_thresholds.novelty_floor
  and a_t.usefulness_score < stop_guard_thresholds.usefulness_floor
  and b_t.reward_score < stop_guard_thresholds.reward_floor
)

controller_stop_requested_t = (d_t.action = "stop")
controller_stop_accepted_t = (
  controller_stop_requested_t
  and runtime_round_index >= stop_guard_thresholds.min_round_index
)

stop_reason =
  "budget_exhausted"         if budget_exhausted_t
  else "no_open_node"        if no_open_node_t
  else "exhausted_low_gain"  if low_gain_branch_t
  else "controller_stop"     if controller_stop_accepted_t
  else null

continue_flag = (stop_reason = null)
```

## Notation Legend

```text
F_{t+1} := FrontierState_t1
d_t := SearchControllerDecision_t
a_t := BranchEvaluation_t
b_t := NodeRewardBreakdown_t
```

## Read Set

- `FrontierState_t1.remaining_budget`
- `FrontierState_t1.open_frontier_node_ids`
- `SearchControllerDecision_t.action`
- `BranchEvaluation_t.branch_exhausted`
- `BranchEvaluation_t.novelty_score`
- `BranchEvaluation_t.usefulness_score`
- `NodeRewardBreakdown_t.reward_score`
- `stop_guard_thresholds`
- `runtime_round_index`

## Derived / Intermediate

- `budget_exhausted_t` 与 `no_open_node_t` 是 runtime 强停止条件，不受控制器建议影响。
- `low_gain_branch_t` 把 exhausted + novelty/usefulness/reward floor 组合成统一低增益谓词。
- direct-stop 路径下的 `F_{t+1}` 是由 runtime 做 identity carry-forward 得到的 frontier snapshot，`a_t / b_t` 则来自 active node 的已缓存 branch judgment / reward。
- `controller_stop_requested_t` 只是建议；只有满足 runtime guard 才会变成 `controller_stop_accepted_t`。

## Write Set

- `stop_reason`
- `continue_flag`

## 输入 payload

- [[FrontierState_t1]]
- [[SearchControllerDecision_t]]
- [[BranchEvaluation_t]]
- [[NodeRewardBreakdown_t]]

## 输出 payload

- stop_reason / continue_flag

## 不确定性边界 / 说明

- stop 最终由 runtime guard 决定，控制器只能建议，不能直接终止 run。

## 相关

- [[operator-map]]
- [[expansion-trace]]
- [[FrontierState_t1]]
- [[SearchControllerDecision_t]]
- [[BranchEvaluation_t]]
- [[NodeRewardBreakdown_t]]
