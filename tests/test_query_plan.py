from cv_match.models import QueryTermCandidate
from cv_match.retrieval.query_plan import (
    canonicalize_controller_query_terms,
    select_query_terms,
    serialize_keyword_query,
)


def test_query_plan_enforces_round_budget() -> None:
    terms = canonicalize_controller_query_terms([" python ", "resume matching"], 1)
    assert terms == ["python", "resume matching"]


def test_query_plan_serializes_terms_with_quotes() -> None:
    assert serialize_keyword_query(["python", 'resume matching', 'Pydantic "AI"']) == (
        'python "resume matching" "Pydantic \\"AI\\""'
    )


def test_query_plan_selects_only_active_terms() -> None:
    pool = [
        QueryTermCandidate(
            term="python",
            source="jd",
            category="role_anchor",
            priority=1,
            evidence="title",
            first_added_round=0,
        ),
        QueryTermCandidate(
            term="resume matching",
            source="notes",
            category="domain",
            priority=2,
            evidence="notes",
            first_added_round=0,
        ),
        QueryTermCandidate(
            term="trace",
            source="reflection",
            category="expansion",
            priority=3,
            evidence="reflection",
            first_added_round=1,
            active=False,
        ),
    ]

    assert select_query_terms(pool, 1) == ["python", "resume matching"]
