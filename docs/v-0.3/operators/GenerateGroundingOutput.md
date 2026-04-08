# GenerateGroundingOutput

把知识库检索结果与 grounding 草稿归一化为 round-0 可消费的结构化启动结果。

## Signature

```text
GenerateGroundingOutput : (RequirementSheet, KnowledgeRetrievalResult, GroundingDraft) -> GroundingOutput
```

## Notation Legend

```text
K := KnowledgeRetrievalResult
R := RequirementSheet
G := GroundingDraft
O := GroundingOutput
```

## Input Projection

```text
routing_mode_t = K.routing_mode
retrieved_cards_t = K.retrieved_cards
selected_domain_pack_ids_t = K.selected_domain_pack_ids
negative_signal_terms_t = K.negative_signal_terms
draft_evidence_cards_t = G.grounding_evidence_cards
draft_seed_specs_t = G.frontier_seed_specifications
must_have_t = R.must_have_capabilities
preferred_t = R.preferred_capabilities
role_title_t = R.role_title
role_summary_t = R.role_summary
location_constraints_t = R.hard_constraints.locations
```

## Primitive Predicates / Matching Rules

```text
normalized_text(text) = trim(compress_whitespace(text))
```

```text
coverage_count_t(seed_spec_t) =
  |stable_deduplicate(seed_spec_t.expected_coverage ∩ must_have_t)|
```

```text
preferred_coverage_count_t(seed_spec_t) =
  |stable_deduplicate(seed_spec_t.expected_coverage ∩ preferred_t)|
```

```text
source_card_rank_t(seed_spec_t) =
  first index in selected_domain_pack_ids_t
  matched by any supporting source card
  else 999
```

```text
first_occurrence_by_key(rows_t, key_t) =
  [
    rows_t[index_t]
    for index_t in range(0, |rows_t|)
    if key_t(rows_t[index_t]) not in {
      key_t(rows_t[j])
      for j in range(0, index_t)
    }
  ]
```

```text
allowed_evidence_types_t = {
  "title_alias",
  "query_term",
  "must_have_link",
  "preferred_link",
  "generic_requirement"
}
```

```text
split_role_title_t(text) =
  stable_deduplicate(
    drop_empty(split_on_any(text, ["/", ",", "(", ")", "-", "|"]))
  )
```

```text
summary_anchor_t =
  normalized_text(role_summary_t)
  if normalized_text(role_summary_t) != ""
  else role_title_t

title_token_terms_t =
  split_role_title_t(role_title_t)[0 : 2]

generic_anchor_terms_t =
  stable_deduplicate(
    [role_title_t, summary_anchor_t]
    + title_token_terms_t
    + preferred_t[0 : 1]
  )[0 : 4]
```

## Transformation

### Phase 1 — Supporting Card Selection

```text
candidate_support_cards_t =
  []
  if routing_mode_t = "generic_fallback"
  else
    [
      row.card
      for row in stable_sort_desc(
        [
          {
            card: card_t,
            must_cover: |stable_deduplicate(card_t.must_have_links ∩ must_have_t)|,
            pref_cover: |stable_deduplicate(card_t.preferred_links ∩ preferred_t)|,
            confidence_rank:
              3 if card_t.confidence = "high"
              else 2 if card_t.confidence = "medium"
              else 1
          }
          for card_t in retrieved_cards_t
          if card_t.confidence != "low"
        ],
        key = (must_cover, pref_cover, confidence_rank)
      )[0 : 4]
    ]
```

### Phase 2 — Evidence Card Normalization

```text
grounding_evidence_cards_t =
  [
    card_t
    for card_t in draft_evidence_cards_t
    if card_t.source_card_id in {support_t.card_id for support_t in candidate_support_cards_t}
       and card_t.evidence_type in allowed_evidence_types_t
  ]
  if routing_mode_t != "generic_fallback"
  else
    [
      {
        source_card_id: "generic.requirement.role_title",
        label: role_title_t,
        rationale: "generic fallback role title anchor",
        evidence_type: "generic_requirement",
        confidence: "high"
      }
    ]
    + (
      [
        {
          source_card_id: "generic.requirement.must_have.0",
          label: must_have_t[0],
          rationale: "generic fallback first must-have",
          evidence_type: "generic_requirement",
          confidence: "high"
        }
      ]
      if |must_have_t| >= 1
      else []
    )
    + (
      [
        {
          source_card_id: "generic.requirement.must_have.1",
          label: must_have_t[1],
          rationale: "generic fallback second must-have",
          evidence_type: "generic_requirement",
          confidence: "high"
        }
      ]
      if |must_have_t| >= 2
      else []
    )
```

```text
if routing_mode_t != "generic_fallback" and |grounding_evidence_cards_t| = 0 and |candidate_support_cards_t| > 0:
  grounding_evidence_cards_t =
    [
      {
        source_card_id: candidate_support_cards_t[0].card_id,
        label: candidate_support_cards_t[0].title,
        rationale: "auto-filled from highest-ranked supporting card",
        evidence_type: "title_alias",
        confidence: candidate_support_cards_t[0].confidence
      }
    ]
```

### Phase 3 — Seed Normalization

```text
normalized_seed_specs_t =
  [
    {
      operator_name: seed_spec_t.operator_name,
      seed_terms: stable_deduplicate(seed_spec_t.seed_terms)[0 : 4],
      seed_rationale: normalized_text(seed_spec_t.seed_rationale),
      source_card_ids:
        [
          source_card_id
          for source_card_id in seed_spec_t.source_card_ids
          if source_card_id in {support_t.card_id for support_t in candidate_support_cards_t}
        ],
      expected_coverage:
        stable_deduplicate(seed_spec_t.expected_coverage)
        if |seed_spec_t.expected_coverage| > 0
        else stable_deduplicate(
          union_of(
            card_t.must_have_links ∪ card_t.preferred_links
            for card_t in candidate_support_cards_t
            if card_t.card_id in seed_spec_t.source_card_ids
          )
        ),
      negative_terms:
        stable_deduplicate(seed_spec_t.negative_terms + negative_signal_terms_t)
    }
    for seed_spec_t in draft_seed_specs_t
    if seed_spec_t.operator_name in {"must_have_alias", "strict_core", "domain_company"}
       and all(
         source_card_id in {support_t.card_id for support_t in candidate_support_cards_t}
         for source_card_id in seed_spec_t.source_card_ids
       )
  ]
  if routing_mode_t != "generic_fallback"
  else
    (
      [
        {
          operator_name: "must_have_alias",
          seed_terms:
            stable_deduplicate(
              [role_title_t]
              + title_token_terms_t[0 : 1]
              + must_have_t[0 : 1]
            )[0 : 4],
          seed_rationale: "role_title_anchor",
          source_card_ids: [],
          expected_coverage: stable_deduplicate(must_have_t[0 : 1]),
          negative_terms: negative_signal_terms_t,
          target_location: null
        },
        {
          operator_name: "must_have_alias",
          seed_terms:
            stable_deduplicate(
              must_have_t[0 : 2]
              + preferred_t[0 : 1]
              + generic_anchor_terms_t
            )[0 : 4],
          seed_rationale: "must_have_core",
          source_card_ids: [],
          expected_coverage: stable_deduplicate(must_have_t[0 : 2]),
          negative_terms: negative_signal_terms_t,
          target_location: null
        },
        {
          operator_name: "strict_core",
          seed_terms:
            stable_deduplicate(
              must_have_t[2 : 4]
              + generic_anchor_terms_t
            )[0 : 4],
          seed_rationale: "coverage_repair",
          source_card_ids: [],
          expected_coverage: stable_deduplicate(must_have_t[2 : 4]),
          negative_terms: negative_signal_terms_t,
          target_location: null
        }
      ]
      + [
        {
          operator_name: "strict_core",
          seed_terms:
            stable_deduplicate(
              [repair_target_t]
              + generic_anchor_terms_t
            )[0 : 4],
          seed_rationale: "must_have_repair",
          source_card_ids: [],
          expected_coverage: [repair_target_t],
          negative_terms: negative_signal_terms_t,
          target_location: null
        }
        for repair_target_t in must_have_t[4 : 6]
      ]
    )
```

### Phase 4 — Seed Ranking and Bounds

```text
ranked_seed_specs_t =
  normalized_seed_specs_t
  if routing_mode_t = "generic_fallback"
  else
    stable_sort_desc(
      normalized_seed_specs_t,
      key = (
        coverage_count_t(seed_spec_t),
        preferred_coverage_count_t(seed_spec_t),
        -source_card_rank_t(seed_spec_t),
        1 if normalized_text(seed_spec_t.seed_rationale) != "" else 0
      )
    )
```

```text
bounded_seed_specs_t =
  first_occurrence_by_key(
    [
      {
        operator_name: seed_spec_t.operator_name,
        seed_terms: stable_deduplicate(seed_spec_t.seed_terms)[0 : 4],
        seed_rationale: seed_spec_t.seed_rationale,
        source_card_ids: seed_spec_t.source_card_ids,
        expected_coverage: seed_spec_t.expected_coverage,
        negative_terms: seed_spec_t.negative_terms,
        target_location:
          location_constraints_t[0] if |location_constraints_t| = 1 else null
      }
      for seed_spec_t in ranked_seed_specs_t
      if |stable_deduplicate(seed_spec_t.seed_terms)| >= 2
    ][0 : 5],
    key = (operator_name, seed_terms, target_location)
  )
```

```text
if |bounded_seed_specs_t| < 3:
  fail("insufficient_seed_specifications")
```

### Field-Level Output Assembly

```text
O.grounding_evidence_cards = grounding_evidence_cards_t
O.frontier_seed_specifications = bounded_seed_specs_t
```

## Defaults / Thresholds Used Here

```text
supporting cards are capped at 4
seed specifications are capped at 3-5 branches
each branch is capped at 2-4 terms
```

## Read Set

- `RequirementSheet.must_have_capabilities`
- `RequirementSheet.preferred_capabilities`
- `RequirementSheet.role_title`
- `RequirementSheet.role_summary`
- `RequirementSheet.hard_constraints.locations`
- `KnowledgeRetrievalResult.routing_mode`
- `KnowledgeRetrievalResult.selected_domain_pack_ids`
- `KnowledgeRetrievalResult.retrieved_cards`
- `KnowledgeRetrievalResult.negative_signal_terms`
- `GroundingDraft.grounding_evidence_cards`
- `GroundingDraft.frontier_seed_specifications`

## Write Set

- `GroundingOutput.grounding_evidence_cards`
- `GroundingOutput.frontier_seed_specifications`

## 输入 payload

- [[RequirementSheet]]
- [[KnowledgeRetrievalResult]]
- [[GroundingDraft]]

## 输出 payload

- [[GroundingOutput]]

## 不确定性边界 / 说明

- `GenerateGroundingOutput` 自身不再调用 LLM；LLM 黑盒已经停留在 `GroundingDraft` 上游。
- 非 generic 模式下，evidence card 必须同时通过 `source_card_id` 与 `evidence_type` whitelist；非法 `evidence_type` 直接丢弃，不做自由修复。
- `generic_fallback` 下 evidence 必须使用 `generic.requirement.*` 虚拟 id，不得读取或发明领域公司线索。
- `generic_fallback` 下不得产出 `domain_company` 或 `crossover_compose` seed；repair seed 只用于补 still-uncovered must-have。
- generic seed synthesis 只使用固定顺序与切片，不允许未加 guard 的位置索引。

## 相关

- [[operator-spec-style]]
- [[RequirementSheet]]
- [[KnowledgeRetrievalResult]]
- [[GroundingDraft]]
- [[GroundingOutput]]
- [[GroundingCatalog]]
- [[grounding-semantics]]
