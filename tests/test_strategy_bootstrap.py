from cv_match.controller.strategy_bootstrap import build_cts_query_from_strategy
from cv_match.models import FilterCondition, SearchStrategy


def test_strategy_filters_are_split_into_cts_safe_query_and_runtime_only_notes() -> None:
    strategy = SearchStrategy(
        must_have_keywords=["python", "retrieval"],
        preferred_keywords=["trace"],
        negative_keywords=["frontend"],
        hard_filters=[
            FilterCondition(
                field="location",
                value="上海",
                source="notes",
                rationale="Prefer Shanghai-based candidates.",
                strictness="hard",
                operator="contains",
            ),
            FilterCondition(
                field="years_experience",
                value=5,
                source="jd",
                rationale="Need senior enough candidates.",
                strictness="hard",
                operator="gte",
            ),
        ],
        soft_filters=[
            FilterCondition(
                field="school",
                value="复旦大学",
                source="notes",
                rationale="Strong education signal.",
                strictness="soft",
                operator="contains",
            ),
            FilterCondition(
                field="industry",
                value="招聘科技",
                source="notes",
                rationale="HR tech experience is useful.",
                strictness="soft",
                operator="contains",
            ),
        ],
        search_rationale="Test strategy-to-query projection.",
    )

    query = build_cts_query_from_strategy(
        strategy=strategy,
        target_new=5,
        exclude_ids=["seen-1"],
    )

    assert [item.field for item in query.hard_filters] == ["location"]
    assert [item.field for item in query.soft_filters] == ["school"]
    assert query.exclude_ids == ["seen-1"]
    assert query.keyword_query == "python retrieval trace"
    assert all(item.field in {"company", "position", "school", "work_content", "location"} for item in query.hard_filters + query.soft_filters)
    assert any("years_experience" in note for note in query.adapter_notes)
    assert any("industry" in note for note in query.adapter_notes)
