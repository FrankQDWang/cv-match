# SeekTalent v0.3 Trace Spec

> 本页是 `v0.3 trace` 的唯一 owner。
> 它只定义 trace taxonomy、audience、render rule、模板和 case 规则。
> trace 是 offline artifact，不是 runtime payload，不进入 `payloads/`。

## 1. 总结论

`v0.3 trace = 双视图，单事实源。`

- `Agent Trace`：给 Codex、Claude Code、LLM-as-a-judge 和工程回放使用。
- `Business Trace`：给业务读者做可读复盘使用。
- 两者必须共享同一个 `case_id`、同一 operator 顺序、同一 terminal outcome。
- `Business Trace` 只能降噪、翻译、压缩，不得新增或改写事实。

## 2. Artifact Taxonomy

### 2.1 类型

- `[[trace-index]]`：trace 导航入口。
- `traces/agent/*`：agent/judge 友好的 case artifact。
- `traces/business/*`：业务可读的 paired case artifact。

### 2.2 命名规则

- agent 文件：`trace-agent-{case_id}.md`
- business 文件：`trace-business-{case_id}.md`
- `case_id` 必须全局唯一，使用 kebab-case。

### 2.3 单事实源规则

- 同一个 case 的事实基线以 `Agent Trace` 为准。
- `Business Trace` 的 operator 顺序、terminal outcome、工具调用类型必须与 paired `Agent Trace` 对齐。
- `Business Trace` 可以删除技术细节，但不能删除整步 operator。

## 3. Required Case Matrix

以下 case 必须始终成对存在：

- `case-bootstrap-explicit-domain`
- `case-bootstrap-inferred-single-domain`
- `case-bootstrap-inferred-dual-domain`
- `case-bootstrap-generic-fallback`
- `case-crossover-legal`
- `case-crossover-illegal-reject`
- `case-stop-controller-direct-accepted`
- `case-stop-controller-direct-rejected`
- `case-stop-exhausted-low-gain-and-finalize`

不再保留旧的“单个 worked example + 零散 routing trace”模式。

## 4. Agent Trace Template

每份 `Agent Trace` 固定 6 段：

1. `Trace Meta`
2. `Scenario Inputs`
3. `Operator Steps`
4. `Invariant Checks`
5. `Terminal Outcome`
6. `Judge Packet`

### 4.1 Step Schema

每个 operator step 必须固定展示：

- `operator_name`
- `operator_inputs`
- `tools_or_services`
- `operator_outputs`
- `key_assertions`
- `failure_or_reject_reason` if any

若该 step 包含 LLM 调用，对应底层审计快照还必须至少保留：

- `output_mode`
- `retries`
- `output_retries`
- `validator_retry_count`
- `model_name`
- `instruction_id_or_hash`
- `message_history_mode`
- `tools_enabled`
- `model_settings_snapshot` 或稳定 hash

其中 `message_history_mode` 在 `v0.3` 的默认 `pydantic-ai` 实现下应固定为 `fresh`；若发生结构化校验失败后的单次 retry，则记为 `fresh+retry_prompt`。`tools_enabled` 应固定为 `false`。

### 4.2 Judge Packet Schema

每份 `Agent Trace` 的 `Judge Packet` 必须固定包含：

- `expected_route`
- `expected_allowed_operators`
- `expected_tool_calls`
- `expected_terminal_state`
- `must_hold`
- `must_not_hold`

### 4.3 表达要求

- 使用 canonical 名、payload 名和 operator 名。
- 可以展示 object id、frontier node id、semantic hash、raw score、guard 名称。
- trace 中出现的 `frontier_node_id / child_frontier_node_id / donor_frontier_node_id` 可以使用人类可读的 case-local 示例 id；它们只是渲染别名，不是 runtime id owner。
- 若需要表达正式 id 生成规则，只能引用 [[InitializeFrontierState]] 与 [[MaterializeSearchExecutionPlan]] 的 owner 规则，trace 不再定义第二套命名规范。
- 优先用短 YAML / JSON 风格快照，不写长叙事。
- 必须让 judge 不查其他文档也能做 case-level 判定。

## 5. Business Trace Template

每份 `Business Trace` 固定 5 段：

1. `场景背景`
2. `系统路线选择`
3. `逐步处理记录`
4. `最终结果`
5. `业务解读与风险`

### 5.1 Step Schema

每步必须使用一算子一步，不允许跨算子合并。

每步固定展示：

- 步骤名：`业务名称（OperatorName）`
- 系统拿到了什么
- 调用了什么工具/服务
- 产出了什么
- 对业务意味着什么

### 5.2 保留 / 删除规则

默认保留：

- operator 名
- 输入 / 输出的业务语义
- `CTS.search`、`RerankService`、本地知识库、LLM、runtime guard 等工具/服务调用
- shortlist 变化
- stop 原因
- 明显的 reject 原因

默认删除：

- 数学记号
- 公式
- semantic hash
- frontier node id
- raw score 向量
- whitelist / clamp / merge 等内部实现细节

## 6. Tool / Service Vocabulary

trace 中允许使用的标准工具/服务名称如下：

- `RequirementExtractionLLM`
- `GroundingGenerationLLM`
- `SearchControllerDecisionLLM`
- `BranchOutcomeEvaluationLLM`
- `SearchRunFinalizationLLM`
- `local grounding knowledge base snapshot`
- `CTS.search`
- `RerankService`
- `runtime deterministic logic`
- `runtime stop guard`

`Business Trace` 可以把这些翻译成业务语言，但括号中应保留 canonical 名。

## 7. Scope Rules

- trace 可以从任意稳定 payload 快照起步，不要求每个 case 都从 `SearchInputTruth` 开始。
- 只要 `Scenario Inputs` 写清起点，case 可以覆盖 bootstrap、single expansion、reject、direct-stop 或 finalize。
- trace 不新增 payload owner，不定义第二套 schema。

## 8. Destructive Update Rules

- 不保留旧 trace 命名作为 alias。
- 不再保留旧 worked trace 作为 owner 或默认入口。
- 所有旧 trace 引用必须收敛到 `[[trace-index]]` 或具体新 case。

## 相关

- [[trace-index]]
- [[design]]
- [[evaluation]]
- [[implementation-checklist]]
