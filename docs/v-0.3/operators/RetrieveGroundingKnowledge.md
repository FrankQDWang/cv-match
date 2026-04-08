# RetrieveGroundingKnowledge

从本地知识库快照中检索与当前岗位最相关的结构化 knowledge cards。

## Signature

```text
RetrieveGroundingKnowledge : (RequirementSheet, BusinessPolicyPack, GroundingKnowledgeBaseSnapshot, KnowledgeRetrievalBudget) -> KnowledgeRetrievalResult
```

## Notation Legend

```text
B := BusinessPolicyPack
KB := GroundingKnowledgeBaseSnapshot
R := RequirementSheet
K := KnowledgeRetrievalResult
```

## Input Projection

```text
explicit_domain_pack_ids_t = stable_deduplicate(B.domain_pack_ids)
role_title_t = R.role_title
must_have_t = R.must_have_capabilities
preferred_t = R.preferred_capabilities
preferred_domains_t = R.preferences.preferred_domains
preferred_backgrounds_t = R.preferences.preferred_backgrounds
exclusion_t = R.exclusion_signals
max_cards_t = KnowledgeRetrievalBudget.max_cards
max_inferred_domain_packs_t = KnowledgeRetrievalBudget.max_inferred_domain_packs
```

```text
card_pool_t =
  runtime-resolved list of GroundingKnowledgeCard
  addressed by KB.snapshot_id and KB.card_ids
```

## Primitive Predicates / Matching Rules

```text
normalized(text) = trim(lowercase(text))
```

```text
lexical_hit(text, terms) =
  1 if ∃ term in terms : normalized(text) contains normalized(term)
  else 0
```

```text
distinct_hits(values, terms) =
  |{
    value
    for value in values
    if lexical_hit(value, terms) = 1
  }|
```

```text
confidence_rank("high") = 3
confidence_rank("medium") = 2
confidence_rank("low") = 1
```

## Transformation

### Phase 1 — Routing

```text
explicit_domain_pack_ids_valid_t =
  all(pack_id in KB.domain_pack_ids for pack_id in explicit_domain_pack_ids_t)

if |explicit_domain_pack_ids_t| > 0 and not explicit_domain_pack_ids_valid_t:
  fail("unknown_domain_pack_id")

if |explicit_domain_pack_ids_t| > 2:
  fail("too_many_explicit_domain_packs")
```

```text
pack_score_t(pack_id) =
  4 * title_alias_hit_any_t(pack_id)
  + 3 * must_have_link_hits_t(pack_id)
  + 1 * preferred_link_hits_t(pack_id)
  - 3 * exclusion_conflicts_t(pack_id)
```

```text
title_alias_hit_any_t(pack_id) =
  1 if ∃ card_t in card_pool_t :
        card_t.domain_id = pack_id
        and lexical_hit(role_title_t, [card_t.title] ∪ card_t.aliases ∪ card_t.canonical_terms) = 1
  else 0

must_have_link_hits_t(pack_id) =
  |supported_must_haves_t(pack_id)|

supported_must_haves_t(pack_id) =
  {
    must_have
    for must_have in must_have_t
    if lexical_hit(
      must_have,
      union_of(
        [card_t.title] ∪ card_t.aliases ∪ card_t.canonical_terms ∪ card_t.must_have_links ∪ card_t.query_terms
        for card_t in card_pool_t if card_t.domain_id = pack_id
      )
    ) = 1
  }

preferred_link_hits_t(pack_id) =
  distinct_hits(
    preferred_t ∪ preferred_domains_t ∪ preferred_backgrounds_t,
    union_of(
      card_t.preferred_links ∪ card_t.query_terms ∪ card_t.canonical_terms
      for card_t in card_pool_t if card_t.domain_id = pack_id
    )
  )

exclusion_conflicts_t(pack_id) =
  distinct_hits(
    exclusion_t,
    union_of(
      card_t.positive_signals ∪ card_t.query_terms
      for card_t in card_pool_t
      if card_t.domain_id = pack_id and card_t.confidence != "low"
    )
  )
```

```text
ranked_domain_packs_t =
  stable_sort_desc(
    [
      {domain_pack_id: pack_id, score: pack_score_t(pack_id)}
      for pack_id in KB.domain_pack_ids
    ],
    key = score
  )[0 : max_inferred_domain_packs_t]
```

```text
top1_t = ranked_domain_packs_t[0] if |ranked_domain_packs_t| >= 1 else null
top2_t = ranked_domain_packs_t[1] if |ranked_domain_packs_t| >= 2 else null

single_inferred_t =
  top1_t != null
  and top1_t.score >= 5
  and (top2_t = null or top1_t.score - top2_t.score >= 2)

dual_inferred_t =
  top1_t != null
  and top2_t != null
  and top1_t.score >= 5
  and top2_t.score >= 5
  and top1_t.score - top2_t.score < 2
  and |supported_must_haves_t(top1_t.domain_pack_id) - supported_must_haves_t(top2_t.domain_pack_id)| > 0
  and |supported_must_haves_t(top2_t.domain_pack_id) - supported_must_haves_t(top1_t.domain_pack_id)| > 0
```

```text
routing_mode_t =
  "explicit_domain" if |explicit_domain_pack_ids_t| > 0
  else "inferred_domain" if single_inferred_t or dual_inferred_t
  else "generic_fallback"

selected_domain_pack_ids_t =
  explicit_domain_pack_ids_t
  if routing_mode_t = "explicit_domain"
  else [top1_t.domain_pack_id]
  if single_inferred_t
  else [top1_t.domain_pack_id, top2_t.domain_pack_id]
  if dual_inferred_t
  else []
```

```text
routing_confidence_t =
  1.0 if routing_mode_t = "explicit_domain"
  else 0.8 if routing_mode_t = "inferred_domain" and |selected_domain_pack_ids_t| = 1
  else 0.7 if routing_mode_t = "inferred_domain" and |selected_domain_pack_ids_t| = 2
  else 0.3

fallback_reason_t =
  null if routing_mode_t != "generic_fallback"
  else "no_domain_pack_scored_above_threshold"
```

### Phase 2 — Card Match

```text
candidate_cards_t =
  []
  if routing_mode_t = "generic_fallback"
  else
    [
      card_t
      for card_t in card_pool_t
      if card_t.domain_id in selected_domain_pack_ids_t
    ]
```

```text
role_query_terms_t =
  stable_deduplicate(
    [role_title_t]
    + must_have_t
    + preferred_t
    + preferred_domains_t
    + preferred_backgrounds_t
  )
```

```text
card_score_t(card_t) =
  4 * title_or_alias_overlap_t(card_t)
  + 2 * must_have_overlap_t(card_t)
  + 1 * preferred_overlap_t(card_t)
  + 1 * query_term_overlap_t(card_t)
  - 2 * negative_signal_conflict_t(card_t)
```

```text
title_or_alias_overlap_t(card_t) =
  1 if lexical_hit(role_title_t, [card_t.title] ∪ card_t.aliases ∪ card_t.canonical_terms) = 1
  else 0

must_have_overlap_t(card_t) =
  distinct_hits(must_have_t, card_t.must_have_links ∪ card_t.query_terms ∪ card_t.canonical_terms)

preferred_overlap_t(card_t) =
  distinct_hits(preferred_t ∪ preferred_domains_t ∪ preferred_backgrounds_t, card_t.preferred_links)

query_term_overlap_t(card_t) =
  distinct_hits(role_query_terms_t, card_t.query_terms)

negative_signal_conflict_t(card_t) =
  distinct_hits(exclusion_t, card_t.positive_signals ∪ card_t.query_terms)
```

```text
matched_cards_t =
  []
  if routing_mode_t = "generic_fallback"
  else
    [
      row.card
      for row in stable_sort_desc(
        [
          {card: card_t, score: card_score_t(card_t)}
          for card_t in candidate_cards_t
        ],
        key = (score, confidence_rank(card.confidence), card.freshness_date, inverse(card.card_id))
      )[0 : max_cards_t]
    ]
```

### Phase 3 — Negative Signal Projection

```text
negative_signal_terms_t =
  exclusion_t
  if routing_mode_t = "generic_fallback"
  else
    stable_deduplicate(
      union_of(
        card_t.negative_signals
        for card_t in matched_cards_t
        if card_t.confidence != "low"
      )
    )
```

### Field-Level Output Assembly

```text
K.knowledge_base_snapshot_id = KB.snapshot_id
K.routing_mode = routing_mode_t
K.selected_domain_pack_ids = selected_domain_pack_ids_t
K.routing_confidence = routing_confidence_t
K.fallback_reason = fallback_reason_t
K.retrieved_cards = matched_cards_t
K.negative_signal_terms = negative_signal_terms_t
```

## Defaults / Thresholds Used Here

```text
KnowledgeRetrievalBudget.max_cards defaults to 8
KnowledgeRetrievalBudget.max_inferred_domain_packs defaults to 2
```

```text
pack_score =
  4 * title_alias_hit_any
  + 3 * must_have_link_hits
  + 1 * preferred_link_hits
  - 3 * exclusion_conflicts
```

```text
card_score =
  4 * title_or_alias_overlap
  + 2 * must_have_overlap
  + 1 * preferred_overlap
  + 1 * query_term_overlap
  - 2 * negative_signal_conflict
```

## Read Set

- `BusinessPolicyPack.domain_pack_ids`
- `GroundingKnowledgeBaseSnapshot.snapshot_id`
- `GroundingKnowledgeBaseSnapshot.domain_pack_ids`
- `GroundingKnowledgeBaseSnapshot.card_ids`
- `RequirementSheet.role_title`
- `RequirementSheet.must_have_capabilities`
- `RequirementSheet.preferred_capabilities`
- `RequirementSheet.exclusion_signals`
- `RequirementSheet.preferences.preferred_domains`
- `RequirementSheet.preferences.preferred_backgrounds`
- `KnowledgeRetrievalBudget.max_cards`
- `KnowledgeRetrievalBudget.max_inferred_domain_packs`

## Write Set

- `KnowledgeRetrievalResult.knowledge_base_snapshot_id`
- `KnowledgeRetrievalResult.routing_mode`
- `KnowledgeRetrievalResult.selected_domain_pack_ids`
- `KnowledgeRetrievalResult.routing_confidence`
- `KnowledgeRetrievalResult.fallback_reason`
- `KnowledgeRetrievalResult.retrieved_cards`
- `KnowledgeRetrievalResult.negative_signal_terms`

## 输入 payload

- [[RequirementSheet]]
- [[BusinessPolicyPack]]
- [[GroundingKnowledgeBaseSnapshot]]
- [[KnowledgeRetrievalBudget]]

## 输出 payload

- [[KnowledgeRetrievalResult]]

## 不确定性边界 / 说明

- 这是本地知识库 routing + retrieval，不做网络搜索，也不扩张到外部 RAG。
- `explicit_domain / inferred_domain / generic_fallback` 是唯一允许的 routing mode。
- `explicit_domain` 只允许 1-2 个已知领域包；超过上限或引用未知 pack id 时必须 fail-fast。
- 双领域 `inferred_domain` 只在两个 pack 各自补到至少一个不同 must-have 时成立。

## 相关

- [[operator-spec-style]]
- [[RequirementSheet]]
- [[BusinessPolicyPack]]
- [[GroundingKnowledgeBaseSnapshot]]
- [[KnowledgeRetrievalResult]]
- [[KnowledgeRetrievalBudget]]
- [[retrieval-semantics]]
