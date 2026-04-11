# RewriteFitnessWeights

runtime rewrite tuning owner。

```text
RewriteFitnessWeights = {
  must_have_repair,
  anchor_preservation,
  rewrite_coherence,
  provenance_coherence,
  query_length_penalty,
  redundancy_penalty
}
```

## 默认值

```yaml
must_have_repair: 1.4
anchor_preservation: 1.0
rewrite_coherence: 1.2
provenance_coherence: 0.8
query_length_penalty: 0.35
redundancy_penalty: 0.45
```

## Invariants

- 这组权重只影响 GA-lite rewrite fitness，不改 non-crossover rewrite contract。
- `GenerateSearchControllerDecision` 里的 contract filter 先执行，`RewriteFitnessWeights` 只在合法候选之间排序。
- 这组权重属于 runtime tuning，不属于 `BusinessPolicyPack`。

## 相关

- [[GenerateSearchControllerDecision]]
- [[weights-and-thresholds-index]]
