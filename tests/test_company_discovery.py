import pytest

from seektalent.company_discovery.models import CompanyEvidence, TargetCompanyCandidate, TargetCompanyPlan
from seektalent.company_discovery.query_injection import inject_target_company_terms
from seektalent.company_discovery.scheduler import select_company_seed_terms
from seektalent.models import QueryTermCandidate, SentQueryRecord
from seektalent.retrieval.query_plan import canonicalize_controller_query_terms


def _anchor() -> QueryTermCandidate:
    return QueryTermCandidate(
        term="python",
        source="job_title",
        category="role_anchor",
        priority=1,
        evidence="title",
        first_added_round=0,
        retrieval_role="role_anchor",
        queryability="admitted",
        family="role.python",
    )


def _company_term(term: str, family: str, *, first_added_round: int = 2) -> QueryTermCandidate:
    return QueryTermCandidate.model_construct(
        term=term,
        source="company_discovery",
        category="company",
        priority=20,
        evidence="company evidence",
        first_added_round=first_added_round,
        retrieval_role="target_company",
        queryability="admitted",
        active=True,
        family=family,
    )


def test_company_discovery_models_create() -> None:
    evidence = CompanyEvidence(
        title="Volcengine hiring",
        url="https://example.com",
        snippet="ByteDance cloud platform",
        source_type="web",
    )
    candidate = TargetCompanyCandidate(
        name="火山引擎",
        aliases=["Volcengine"],
        source="web_inferred",
        intent="target",
        confidence=0.8,
        fit_axes=["cloud", "platform"],
        search_usage="company_filter",
        evidence=[evidence],
        rationale="Matches the target domain.",
    )
    plan = TargetCompanyPlan(
        explicit_targets=[candidate],
        inferred_targets=[],
        excluded_companies=["Tencent"],
        holdout_companies=[],
        rejected_companies=[],
        stop_reason="done",
    )

    assert plan.explicit_targets[0].evidence[0].url == "https://example.com"
    assert plan.explicit_targets[0].aliases == ["Volcengine"]
    assert plan.stop_reason == "done"


def test_inject_target_company_terms_appends_deduped_company_terms() -> None:
    plan = TargetCompanyPlan(
        explicit_targets=[
            TargetCompanyCandidate(
                name="火山引擎",
                aliases=["Volcengine"],
                source="explicit_jd",
                intent="target",
                confidence=0.9,
                fit_axes=["cloud"],
                search_usage="keyword_and_filter",
                evidence=[],
                rationale="JD named company.",
            ),
            TargetCompanyCandidate(
                name="火山引擎",
                aliases=[],
                source="candidate_backfill",
                intent="target",
                confidence=0.5,
                fit_axes=["cloud"],
                search_usage="keyword_term",
                evidence=[],
                rationale="Duplicate company.",
            ),
        ],
        inferred_targets=[
            TargetCompanyCandidate(
                name="阿里云",
                aliases=["Aliyun"],
                source="web_inferred",
                intent="similar_to_target",
                confidence=0.7,
                fit_axes=["cloud"],
                search_usage="company_filter",
                evidence=[
                    CompanyEvidence(title="Aliyun role", url="https://example.com/a", snippet="Alibaba Cloud", source_type="web"),
                ],
                rationale="Relevant adjacent company.",
            ),
            TargetCompanyCandidate(
                name="腾讯",
                aliases=[],
                source="web_inferred",
                intent="exclude",
                confidence=0.1,
                fit_axes=[],
                search_usage="exclude",
                evidence=[],
                rationale="Should not inject.",
            ),
        ],
        excluded_companies=[],
        holdout_companies=[],
        rejected_companies=[],
        stop_reason=None,
    )
    pool = [
        _anchor(),
        QueryTermCandidate.model_construct(
            term="aliyun",
            source="company_discovery",
            category="company",
            priority=25,
            evidence="existing pool company",
            first_added_round=1,
            retrieval_role="target_company",
            queryability="admitted",
            active=True,
            family="company.aliyun",
        ),
    ]

    injected = inject_target_company_terms(pool, plan, first_added_round=2)

    assert [item.term for item in injected] == ["python", "aliyun", "火山引擎"]
    assert injected[2].category == "company"
    assert injected[2].retrieval_role == "target_company"
    assert injected[2].source == "explicit_jd"
    assert injected[2].queryability == "admitted"
    assert injected[2].active is True
    assert injected[2].priority >= 20
    assert injected[2].family == "company.volcengine"


def test_select_company_seed_terms_picks_first_untried_company() -> None:
    pool = [
        _anchor(),
        _company_term("火山引擎", "company.volcengine"),
        _company_term("阿里云", "company.aliyun"),
    ]

    sent_history = [
        SentQueryRecord(
            round_no=1,
            query_role="exploit",
            batch_no=1,
            requested_count=10,
            query_terms=["python", "火山引擎"],
            keyword_query="python 火山引擎",
            source_plan_version=1,
            rationale="sent",
        )
    ]

    selected = select_company_seed_terms(pool, sent_history, forced_families=set(), max_terms=2)

    assert [item.term for item in selected] == ["python", "阿里云"]


def test_query_plan_accepts_company_terms_without_counting_company_families_as_compiler_duplicates() -> None:
    pool = [
        _anchor(),
        _company_term("火山引擎", "company.volcengine"),
        _company_term("阿里云", "company.volcengine", first_added_round=3),
    ]

    assert canonicalize_controller_query_terms(
        ["python", "火山引擎", "阿里云"],
        round_no=2,
        title_anchor_term="python",
        query_term_pool=pool,
    ) == ["python", "火山引擎", "阿里云"]


def test_query_plan_still_rejects_repeated_non_company_families() -> None:
    pool = [
        _anchor(),
        QueryTermCandidate(
            term="python data",
            source="jd",
            category="domain",
            priority=2,
            evidence="jd",
            first_added_round=0,
            retrieval_role="core_skill",
            queryability="admitted",
            family="domain.python",
        ),
        QueryTermCandidate(
            term="python infra",
            source="jd",
            category="domain",
            priority=3,
            evidence="jd",
            first_added_round=0,
            retrieval_role="core_skill",
            queryability="admitted",
            family="domain.python",
        ),
    ]

    with pytest.raises(ValueError, match="repeat compiler families"):
        canonicalize_controller_query_terms(
            ["python", "python data", "python infra"],
            round_no=2,
            title_anchor_term="python",
            query_term_pool=pool,
        )
