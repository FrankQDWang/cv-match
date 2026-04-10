# BootstrapOutput

round-0 bootstrap 的稳定输出。

```text
BootstrapOutput = { frontier_seed_specifications }
```

## 稳定字段组

- 初始 seeds：`frontier_seed_specifications`

## Direct Producer / Direct Consumers

- Direct producer：[[GenerateBootstrapOutput]]
- Direct consumers：[[InitializeFrontierState]]

## Invariants

- 它只服务 round-0 frontier 初始化。
- routed path 最多生成 `strict_core / must_have_alias / domain_expansion` 三条 seeds。
- generic fallback 固定只生成 `strict_core / must_have_alias` 两条 seeds。

## 相关

- [[FrontierSeedSpecification]]
- [[FrontierState_t]]

