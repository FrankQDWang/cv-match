# Agent Trace: case-bootstrap-ambiguous-close-score-generic

## Trace Meta

```yaml
case_id: case-bootstrap-ambiguous-close-score-generic
routing_mode: generic_fallback
selected_knowledge_pack_id: None
stop_reason: controller_stop
run_dir: /Users/frankqdwang/Agents/SeekTalent/artifacts/runtime/cases/case-bootstrap-ambiguous-close-score-generic
```

## Bootstrap

- routing_mode: `generic_fallback`
- selected_knowledge_pack_id: `None`
- fallback_reason: `top1_top2_gap_below_floor`
- seed_count: `2`

## Runtime Rounds

| round | action | operator | knowledge_pack_id | stop_reason |
| --- | --- | --- | --- | --- |
| 0 | stop | must_have_alias |  | controller_stop |

## Final Result

- shortlist: `[]`
- run_summary: Ambiguous route fell back to generic bootstrap.
