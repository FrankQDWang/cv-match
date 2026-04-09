# Business Trace: case-bootstrap-ambiguous-close-score-generic

## 场景背景

- 场景：接近分数触发 generic
- 业务解释：两个领域分数太接近时，不注入模糊上下文，直接退回 generic。

## 关键信号

- 路由结果：`generic_fallback`
- 领域知识包：`None`
- fallback_reason：`top1_top2_gap_below_floor`
- 终止原因：`controller_stop`
- shortlist：`[]`

## 业务解读

- 该 case 期望走 `generic_fallback`，实际路由为 `generic_fallback`。
- 该 case 期望 stop 为 `controller_stop`，实际 stop 为 `controller_stop`。
- 必须保留的事实：fallback_reason is top1_top2_gap_below_floor; selected_knowledge_pack_id is null。
- 不应出现的事实：domain_company appears in bootstrap seeds。
