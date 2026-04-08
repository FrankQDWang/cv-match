# SeekTalent v0.3 Trace Index

> 本页是 `v0.3 trace` 的统一导航入口。
> trace schema 与规则以 [[trace-spec]] 为准。

## 1. 阅读建议

- 工程实现、回放、LLM-as-a-judge：优先读 `Agent Trace`
- 业务复盘、需求对齐、路线解释：优先读 `Business Trace`
- 两类 trace 必须按同一 `case_id` 成对阅读，不允许混用不同 case

## 2. Case Matrix

| case_id | 场景 | Agent Trace | Business Trace |
| --- | --- | --- | --- |
| `case-bootstrap-explicit-domain` | 显式领域 bootstrap | [[trace-agent-case-bootstrap-explicit-domain]] | [[trace-business-case-bootstrap-explicit-domain]] |
| `case-bootstrap-inferred-single-domain` | 单领域推断 bootstrap | [[trace-agent-case-bootstrap-inferred-single-domain]] | [[trace-business-case-bootstrap-inferred-single-domain]] |
| `case-bootstrap-inferred-dual-domain` | 双领域推断 bootstrap | [[trace-agent-case-bootstrap-inferred-dual-domain]] | [[trace-business-case-bootstrap-inferred-dual-domain]] |
| `case-bootstrap-generic-fallback` | 通用回退 bootstrap | [[trace-agent-case-bootstrap-generic-fallback]] | [[trace-business-case-bootstrap-generic-fallback]] |
| `case-crossover-legal` | 合法 crossover | [[trace-agent-case-crossover-legal]] | [[trace-business-case-crossover-legal]] |
| `case-crossover-illegal-reject` | 非法 crossover 拒绝 | [[trace-agent-case-crossover-illegal-reject]] | [[trace-business-case-crossover-illegal-reject]] |
| `case-stop-controller-direct-accepted` | 控制器 direct-stop 被接受 | [[trace-agent-case-stop-controller-direct-accepted]] | [[trace-business-case-stop-controller-direct-accepted]] |
| `case-stop-controller-direct-rejected` | 控制器 direct-stop 被拒绝 | [[trace-agent-case-stop-controller-direct-rejected]] | [[trace-business-case-stop-controller-direct-rejected]] |
| `case-stop-exhausted-low-gain-and-finalize` | 低增益 stop 并 finalize | [[trace-agent-case-stop-exhausted-low-gain-and-finalize]] | [[trace-business-case-stop-exhausted-low-gain-and-finalize]] |

## 3. 推荐阅读顺序

### 工程读者

1. [[trace-spec]]
2. [[trace-agent-case-bootstrap-explicit-domain]]
3. [[trace-agent-case-bootstrap-generic-fallback]]
4. [[trace-agent-case-crossover-legal]]
5. [[trace-agent-case-stop-controller-direct-accepted]]

### 业务读者

1. [[trace-business-case-bootstrap-explicit-domain]]
2. [[trace-business-case-bootstrap-generic-fallback]]
3. [[trace-business-case-crossover-legal]]
4. [[trace-business-case-stop-controller-direct-accepted]]

## 4. 使用规则

- trace 是 case library，不是 payload owner。
- 默认不再引用旧 worked trace 体系。
- 若只需要一份总入口，一律链接到本页。

## 相关

- [[trace-spec]]
- [[design]]
- [[workflow-explained]]
- [[evaluation]]
