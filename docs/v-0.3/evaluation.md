# SeekTalent v0.3 评估规范

## 0. 文档信息

- 版本：`v0.3`
- 状态：`evaluation / proposed`
- 文档目标：定义 `Knowledge-Grounded Frontier Runtime` 的离线评估口径，回答第一轮是否更稳、排序是否更准、成本是否可控。
- 现状声明：本文定义的是目标评估规范，不表示仓库当前已经具备完整数据集与流水线。

## 1. 评估目标

`v0.3` 的评估不看“query 看起来像不像人写的”，而看：

1. 首轮是否从“零召回 / 长 query”显著改善
2. reranker fusion 后的 shortlist 质量是否提升
3. must-have 与硬约束是否更稳
4. stability risk 是否被正确使用而不误杀低置信度候选
5. frontier crossover 是否带来真实收益
6. 页面成本与 rerank 成本是否值得

## 2. 实验矩阵

推荐固定实验矩阵：

- `E0`: current baseline
- `E1`: `E0` + knowledge retrieval + short seed bootstrap
- `E2`: `E1` + frozen `BusinessPolicyPack + RerankerCalibration + ScoringPolicy`
- `E3`: `E2` + reranker fusion + stability risk
- `E4`: `E3` + crossover compose + updated reward
- `E5`: `E4` + stop / finalize hardening

## 3. 评估对象

每个 case 至少要保留：

- 原始 `SearchInputTruth`
- `BusinessPolicyPack`
- `KnowledgeRetrievalResult`
- `ScoringPolicy`
- 运行中关键 payload snapshot
- 最终 `SearchRunResult`
- 用于 replay / llm-as-a-judge 的 `Agent Trace`
- 用于业务复盘的 paired `Business Trace`

## 4. 指标

### 4.1 Routing 与 Fallback

- explicit hit rate
- inferred single-pack hit rate
- inferred dual-pack hit rate
- generic fallback rate
- fallback 后 round-1 non-empty shortlist rate

### 4.2 首轮启动质量

- round-1 non-empty shortlist rate
- round-1 zero-recall rate
- round-1 unique candidate count
- round-1 must-have coverage
- 平均 seed branch 数
- 平均每个 seed branch 的 term 数

### 4.3 排序质量

- final shortlist 的人工相关性
- must-have 覆盖率
- 硬约束命中率
- reranker normalized score 与人工相关性的单调性
- `fusion_weights` 调整后的排序敏感性

### 4.4 稳定性风险

- `CareerStabilityProfile.confidence_score` 分布
- 低置信度 case 的 penalty 触发率
- `frequent_job_changes` risk flag 的人工正确率
- 开启 / 关闭 stability penalty 后的 shortlist 差异

### 4.5 新颖性与多样性

- 去重后的 unique candidate 数
- shortlist 的 title / company / city 多样性
- semantic hash 命中率
- crossover child 的 net-new fit yield

### 4.6 知识库质量

- `RetrieveGroundingKnowledge` 的回放稳定性
- `routing_mode` 与 `selected_domain_pack_ids` 的回放稳定性
- `source_card_ids` 覆盖率
- high / medium / low confidence cards 的使用比例
- negative/confusion signals 触发后的误召下降幅度

### 4.7 成本

- pages fetched
- latency
- rerank batch 数与 rerank latency
- 每次新增 shortlist 候选的成本

### 4.8 LLM Contract 稳定性

- provider-native strict structured output 成功率
- `validator_retry_count` 分布
- 单次 `output_retries=1` 后仍失败的比例
- 出现 prompted JSON / 自由文本 / fallback model chain 的违规次数

### 4.9 停止行为

- budget exhausted 的比例
- no-open-node 的比例
- exhausted-low-gain stop 的比例
- `controller_stop` 被 runtime 接受的比例

## 5. 固定评审场景

- 已知 3 个领域内的单领域 JD
- 跨 2 个领域的混合 JD
- 完全不落在现有 3 个领域内的 JD
- 低置信度职业稳定性 case
- 高重复低收益 branch
- controller 请求 stop 但未达 runtime floor 的 case

## 6. Trace 审查要求

每次 docs 或实现变更后，必须满足以下 trace 审查要求：

- judge 只读取 `Agent Trace`，不读取 `Business Trace`
- `Business Trace` 只用于业务审查与复盘，不参与打分
- 对应 LLM call 审计快照至少保留 `output_mode / retries / output_retries / validator_retry_count`
- 9 个 `case_id` 必须全部存在 paired trace：
  - `case-bootstrap-explicit-domain`
  - `case-bootstrap-inferred-single-domain`
  - `case-bootstrap-inferred-dual-domain`
  - `case-bootstrap-generic-fallback`
  - `case-crossover-legal`
  - `case-crossover-illegal-reject`
  - `case-stop-controller-direct-accepted`
  - `case-stop-controller-direct-rejected`
  - `case-stop-exhausted-low-gain-and-finalize`
