from __future__ import annotations

import re

from cv_match.models import (
    CTSQuery,
    CTSFilterCondition,
    FilterCondition,
    KeywordAttribution,
    SearchStrategy,
    unique_strings,
)

KEYWORD_PATTERNS: dict[str, tuple[str, ...]] = {
    "python": ("python",),
    "agent": ("agent", "智能体"),
    "LLM application": ("llm", "大模型", "模型应用", "model application"),
    "retrieval": ("retrieval", "检索", "召回"),
    "search": ("search", "搜索"),
    "ranking": ("ranking", "评分", "打分", "rerank"),
    "tracing": ("trace", "tracing", "可观察性", "链路", "追踪"),
    "logging": ("logging", "日志", "event logging", "structured logging"),
    "Pydantic AI": ("pydantic ai", "pydantic-ai"),
    "resume matching": ("resume", "简历", "候选人"),
    "OpenAPI adapter": ("openapi", "接口适配"),
}
NEGATIVE_PATTERNS = {
    "frontend": ("frontend", "react", "前端"),
    "sales": ("sales", "销售"),
    "research": ("research", "算法研究", "paper", "论文"),
}
MANDATORY_HINTS = ("必须", "必备", "要求", "精通", "熟练", "掌握", "经验", "本科", "负责")
PREFERRED_HINTS = ("优先", "加分", "熟悉", "了解", "最好")
NEGATIVE_HINTS = ("不考虑", "排除", "不要", "不接受")
LOCATION_WORDS = ("上海", "北京", "深圳", "杭州", "广州", "武汉", "苏州", "成都")
GENERIC_SKIP_PATTERNS = (
    "负责",
    "项目",
    "实现",
    "每轮",
    "完整",
    "接口适配",
    "寻访须知",
    "岗位职责",
    "任职要求",
)


def bootstrap_search_strategy(*, jd: str, notes: str) -> SearchStrategy:
    combined = f"{jd}\n{notes}"
    jd_lower = jd.casefold()
    notes_lower = notes.casefold()
    lines = [line.strip(" -*\t") for line in combined.splitlines() if line.strip()]
    must_have: list[str] = []
    preferred: list[str] = []
    negative: list[str] = []
    hard_filters: list[FilterCondition] = []
    soft_filters: list[FilterCondition] = []
    attributions: list[KeywordAttribution] = []

    for location in LOCATION_WORDS:
        location_lines = [line for line in lines if location in line]
        if not location_lines:
            continue
        target_list = soft_filters
        strictness = "soft"
        source = "notes" if location in notes else "jd"
        rationale = "Location preference inferred from input text."
        if any(any(hint in line for hint in ("必须", "限定", "only", "base")) for line in location_lines):
            target_list = hard_filters
            strictness = "hard"
            rationale = "Location was expressed as mandatory."
        elif not any(any(hint in line for hint in ("优先", "prefer")) for line in location_lines):
            continue
        target_list.append(
            FilterCondition(
                field="location",
                value=location,
                source=source,
                rationale=rationale,
                strictness=strictness,
                operator="contains",
            )
        )

    for canonical, aliases in KEYWORD_PATTERNS.items():
        in_jd = any(alias.casefold() in jd_lower for alias in aliases)
        in_notes = any(alias.casefold() in notes_lower for alias in aliases)
        if not (in_jd or in_notes):
            continue
        if in_jd:
            must_have.append(canonical)
        elif in_notes:
            preferred.append(canonical)
        attributions.append(
            KeywordAttribution(
                keyword=canonical,
                source="jd" if in_jd else "notes",
                bucket="must_have" if in_jd else "preferred",
                reason="Matched explicit role keyword pattern.",
            )
        )

    for canonical, aliases in NEGATIVE_PATTERNS.items():
        if any(alias.casefold() in notes_lower for alias in aliases):
            negative.append(canonical)
            attributions.append(
                KeywordAttribution(
                    keyword=canonical,
                    source="notes",
                    bucket="negative",
                    reason="Matched explicit exclusion keyword pattern.",
                )
            )

    for line in lines:
        phrases = extract_phrases(line)
        if any(hint in line for hint in NEGATIVE_HINTS):
            for phrase in phrases[:4]:
                negative.append(phrase)
                attributions.append(
                    KeywordAttribution(
                        keyword=phrase,
                        source="notes" if phrase in notes else "jd",
                        bucket="negative",
                        reason="Matched exclusion wording in the input.",
                    )
                )
            continue
        if len(must_have) >= 12 and len(preferred) >= 6:
            continue
        target_bucket = preferred if any(hint in line for hint in PREFERRED_HINTS) else must_have
        bucket_name = "preferred" if target_bucket is preferred else "must_have"
        for phrase in phrases[:3]:
            target_bucket.append(phrase)
            attributions.append(
                KeywordAttribution(
                    keyword=phrase,
                    source="notes" if phrase in notes else "jd",
                    bucket=bucket_name,
                    reason="Extracted from role text using deterministic phrase rules.",
                )
            )

    if not must_have:
        fallback_tokens = extract_phrases(jd)[:8]
        must_have = fallback_tokens or ["Python", "后端开发"]

    must_have = unique_strings(must_have)
    preferred = unique_strings(
        [item for item in preferred if item.casefold() not in {keyword.casefold() for keyword in must_have}]
    )
    negative = unique_strings(negative)
    rationale = (
        f"Use {len(must_have)} must-have keywords and {len(preferred)} preferred keywords "
        f"to drive the next CTS retrieval step."
    )
    return SearchStrategy(
        must_have_keywords=must_have,
        preferred_keywords=preferred,
        negative_keywords=negative,
        hard_filters=hard_filters,
        soft_filters=soft_filters,
        keyword_attributions=attributions,
        search_rationale=rationale,
    ).normalized()


def build_cts_query_from_strategy(
    *,
    strategy: SearchStrategy,
    target_new: int,
    exclude_ids: list[str],
    keywords: list[str] | None = None,
    rationale: str | None = None,
    adapter_notes: list[str] | None = None,
) -> CTSQuery:
    hard_filters, soft_filters, filter_notes = split_cts_safe_filters(strategy)
    return CTSQuery(
        keywords=unique_strings(keywords or strategy.retrieval_keywords),
        keyword_query=" ".join(unique_strings(keywords or strategy.retrieval_keywords)),
        hard_filters=hard_filters,
        soft_filters=soft_filters,
        exclude_ids=exclude_ids,
        page=1,
        page_size=target_new,
        rationale=rationale or strategy.search_rationale,
        adapter_notes=unique_strings((adapter_notes or []) + filter_notes),
    )


def split_cts_safe_filters(strategy: SearchStrategy) -> tuple[list[CTSFilterCondition], list[CTSFilterCondition], list[str]]:
    hard_filters, hard_notes = _convert_filters(strategy.hard_filters, label="hard")
    soft_filters, soft_notes = _convert_filters(strategy.soft_filters, label="soft", reserved_fields={item.field for item in hard_filters})
    return hard_filters, soft_filters, unique_strings(hard_notes + soft_notes)


def _convert_filters(
    filters: list[FilterCondition],
    *,
    label: str,
    reserved_fields: set[str] | None = None,
) -> tuple[list[CTSFilterCondition], list[str]]:
    converted: list[CTSFilterCondition] = []
    notes: list[str] = []
    used_fields = set(reserved_fields or set())
    for filter_item in filters:
        if filter_item.field not in {"company", "position", "school", "work_content", "location"}:
            notes.append(
                f"Strategy {label} filter `{filter_item.field}` is retained for scoring/runtime but is not sent to CTS."
            )
            continue
        if filter_item.field in used_fields:
            notes.append(
                f"Strategy {label} filter `{filter_item.field}` was skipped because CTS payload only keeps one filter per field."
            )
            continue
        converted.append(
            CTSFilterCondition(
                field=filter_item.field,
                value=filter_item.value,
                operator=filter_item.operator,
            )
        )
        used_fields.add(filter_item.field)
    return converted, notes


def extract_phrases(text: str) -> list[str]:
    normalized = re.sub(r"^[#>\-\*\d\.\s]+", "", text).strip()
    parts = re.split(r"[：:，,。；;、\(\)（）/|]", normalized)
    phrases: list[str] = []
    for part in parts:
        clean = re.sub(r"\s+", " ", part).strip(" -*\t")
        if len(clean) < 2:
            continue
        if clean in LOCATION_WORDS:
            continue
        if any(pattern in clean for pattern in GENERIC_SKIP_PATTERNS):
            continue
        if any(hint in clean for hint in MANDATORY_HINTS + PREFERRED_HINTS + NEGATIVE_HINTS):
            continue
        if re.fullmatch(r"[\d\-~至年以上薪Kk/月年 ]+", clean):
            continue
        if len(clean) > 18 and " " not in clean:
            continue
        phrases.append(clean)
    english_terms = re.findall(
        r"[A-Za-z][A-Za-z0-9/\-\+\.]{1,30}(?: [A-Za-z][A-Za-z0-9/\-\+\.]{1,30}){0,2}",
        normalized,
    )
    phrases.extend(english_terms)
    return unique_strings(phrases)
