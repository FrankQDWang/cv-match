# SeekTalent v0.3 评估规范

## 0. 文档信息

- 版本：`v0.3`
- 状态：`evaluation / proposed`
- 文档目标：定义 `Grounded Frontier Runtime` 的离线评估口径，回答质量是否提升、成本是否受控。
- 现状声明：本文定义的是目标评估规范，不表示仓库当前已经具备完整数据集与流水线。

## 1. 评估目标

`v0.3` 的评估不看“query 看起来像不像人写的”，而看：

1. run-global shortlist 质量是否提升
2. must-have 与硬约束是否更稳
3. 重复结果是否减少
4. 页面成本是否更值得
5. frontier runtime 与 grounding 是否带来真实收益

## 2. 实验矩阵

推荐固定实验矩阵：

- `E0`: current baseline
- `E1`: frontier runtime only
- `E2`: `E1` + grounding
- `E3`: `E2` + branch evaluation + reward
- `E4`: `E3` + stop / finalize hardening

## 3. 评估对象

每个 case 至少要保留：

- 原始 `SearchInputTruth`
- 对应 `RequirementSheet`
- 运行中关键 payload snapshot
- 最终 `SearchRunResult`
- 用于回放的 operator trace

## 4. 指标

### 4.1 质量

- final shortlist 的人工相关性
- must-have 覆盖率
- 硬约束命中率

### 4.2 新颖性与多样性

- 去重后的 unique candidate 数
- shortlist 的 title / company / city 多样性
- semantic hash 命中率

### 4.3 成本

- pages fetched
- latency
- 每次新增 shortlist 候选的成本

### 4.4 停止行为

- budget exhausted 的比例
- no-open-node 的比例
- exhausted-low-gain stop 的比例
- controller-suggested stop 被 runtime 接受的比例
