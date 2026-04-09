# SeekTalent v0.3 评估规范

## 0. 当前口径

当前 `HEAD` 自动产出的评估矩阵只覆盖 `E5`。

也就是说，仓库现在关心的是：

- 当前这版 runtime 的 bundle / trace / eval 是否自洽
- bootstrap 路由和关键词注入是否稳定
- 排序、frontier、stop 行为是否可回放

不再回头维护旧的 `E0..E4` 兼容 runner。

## 1. 评估对象

每个 case 至少保留：

- `SearchRunBundle`
- `SearchRunEval`
- paired `Agent Trace`
- paired `Business Trace`

canonical case 还会额外保留：

- `CanonicalCaseSpec`
- `judge_packet.json`

## 2. 当前 E5 关注点

### 2.1 bootstrap 路由

- `routing_mode`
- `selected_knowledge_pack_id`
- `routing_confidence`
- `generic_fallback_correctness`

### 2.2 关键词注入质量

- `include_keyword_adoption`
- `exclude_keyword_leak`
- round-0 shortlist 是否非空
- generic fallback 是否只生成 `strict_core` / `must_have_alias`

### 2.3 排序与 shortlist

- final shortlist 数量
- top candidate id
- rerank + calibration + fusion 是否稳定

### 2.4 frontier 与分支价值

- round count
- average novelty
- average usefulness
- exhausted-low-gain stop 行为

### 2.5 成本

- pages fetched
- deduplicated candidate count
- runtime audit tag count

### 2.6 LLM contract

- `validator_retry_count`
- strict structured output 是否稳定
- 是否出现越权 surface

## 3. 当前 canonical bootstrap cases

bootstrap 固定审查 4 类：

- `case-bootstrap-explicit-domain`
- `case-bootstrap-inferred-top1`
- `case-bootstrap-ambiguous-close-score-generic`
- `case-bootstrap-out-of-domain-generic`

## 4. paired trace 审查要求

- judge 只读 `Agent Trace`
- `Business Trace` 只做业务复盘
- paired trace 必须来自同一个 canonical case bundle
- trace、judge packet、eval 三者必须和 bundle 保持一致

## 5. 审计快照要求

每个 LLM 调用点至少保留：

- `output_mode`
- `retries`
- `output_retries`
- `validator_retry_count`
- `model_name`
- `instruction_id_or_hash`
- `message_history_mode`
- `tools_enabled`
- `model_settings_snapshot`
