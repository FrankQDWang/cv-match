# CTS Enum Observations

Last verified: `2026-04-02`  
Method: live black-box probes against `/thirdCooperate/search/candidate/cts`

This file records only observed behavior. It is not an official CTS contract.
Its role in the doc set is evidence only: it informs runtime-safe enum mapping, but does not define business truth or prompt contracts.

## Confirmed

### `workExperienceRange`

| Code | Observed label | Confidence |
| --- | --- | --- |
| `1` | `1年以下` | high |
| `2` | `1-3年` | high |
| `3` | `3-5年` | high |
| `4` | `5-10年` | high |
| `5` | `10年以上` | high |
| `0/6/7/8` | near-baseline, effectively no filtering | high |

### `age`

| Code | Observed label | Confidence |
| --- | --- | --- |
| `1` | `20-25岁` | high |
| `2` | `25-30岁` | high |
| `3` | `30-35岁` | high |
| `4` | `35-40岁` | high |
| `5` | `40-45岁` | high |
| `6` | `45岁以上` | high |
| `0/7/8/9` | near-baseline, effectively no filtering | high |

### `gender`

| Code | Observed label | Confidence |
| --- | --- | --- |
| `1` | `男` | high |
| `2` | `女` | high |
| `3/4` | near-baseline, effectively no filtering | medium |

### `degree`

| Code | Observed label | Confidence |
| --- | --- | --- |
| `1` | `大专及以上` | high |
| `2` | `本科及以上` | high |
| `3` | `硕士及以上` | high |
| `4/5` | near-baseline, effectively no filtering | medium |

## Partially Confirmed

### `schoolType`

Observed totals were materially different for `1-6`, but only part of the mapping is stable enough to use in runtime today.

| Code | Observed label | Confidence | Runtime use |
| --- | --- | --- | --- |
| `1` | `双一流` | medium | enabled |
| `2` | `211` | medium | enabled |
| `3` | `985` | medium | enabled |
| `4` | unresolved (`强基计划` or another prestige bucket) | low | disabled |
| `5` | unresolved (`双高计划` or another school bucket) | low | disabled |
| `6` | overseas-like bucket | low | disabled |
| `7` | near-baseline, effectively no filtering | high | disabled |

## Runtime policy

- Only high-confidence and medium-confidence mappings that are operationally safe are projected into CTS filters.
- Unresolved enum values stay in `runtime_only_constraints`.
- The runtime does not send synthetic "不限" codes. When a condition resolves to "no safe enum filter", it omits the CTS field entirely.
