from __future__ import annotations

from dataclasses import dataclass

from seektalent.models import (
    BusinessPolicyPack,
    ExplanationPreferences,
    FitGateConstraints,
    FusionWeightPreferences,
    GroundingKnowledgeBaseSnapshot,
    GroundingKnowledgeCard,
    KnowledgeRetrievalBudget,
    RerankerCalibration,
    RuntimeSearchBudget,
    StabilityPolicy,
)


DEFAULT_OPERATOR_CATALOG = (
    "must_have_alias",
    "strict_core",
    "domain_company",
    "crossover_compose",
)


@dataclass(frozen=True)
class BootstrapAssets:
    business_policy_pack: BusinessPolicyPack
    knowledge_base_snapshot: GroundingKnowledgeBaseSnapshot
    knowledge_cards: tuple[GroundingKnowledgeCard, ...]
    reranker_calibration: RerankerCalibration
    knowledge_retrieval_budget: KnowledgeRetrievalBudget
    runtime_search_budget: RuntimeSearchBudget
    operator_catalog: tuple[str, ...]


def default_bootstrap_assets() -> BootstrapAssets:
    knowledge_cards = (
        _knowledge_card(
            card_id="role_alias.llm_agent_rag_engineering.backend_agent_engineer",
            domain_id="llm_agent_rag_engineering",
            report_type="role_family",
            card_type="role_alias",
            title="LLM/Agent Backend Engineer",
            summary="Agent、RAG、LLM application 的后端与平台研发角色。",
            canonical_terms=["agent engineer", "rag engineer"],
            aliases=["llm application engineer", "ai backend engineer"],
            positive_signals=["tool calling", "workflow orchestration", "retrieval pipeline"],
            negative_signals=["data analyst", "pure prompt operations"],
            query_terms=["agent engineer", "rag", "python"],
            must_have_links=["Python backend", "LLM application"],
            preferred_links=["workflow orchestration", "to-b delivery"],
            confidence="high",
            source_report_ids=["report.role_family.llm_agent_rag_engineering.codex_synthesis_2026_04_07"],
            source_model_votes=2,
            freshness_date="2026-04-07",
        ),
        _knowledge_card(
            card_id="business_vertical.llm_agent_rag_engineering.enterprise_agent_delivery",
            domain_id="llm_agent_rag_engineering",
            report_type="business_vertical",
            card_type="business_vertical",
            title="Enterprise Agent Delivery",
            summary="面向 to-b agent 产品交付、workflow orchestration 和上线治理。",
            canonical_terms=["enterprise agent", "to-b ai delivery"],
            aliases=["b2b ai delivery", "enterprise llm"],
            positive_signals=["customer delivery", "workflow orchestration"],
            negative_signals=["pure research"],
            query_terms=["enterprise agent", "workflow orchestration", "to-b"],
            must_have_links=["LLM application"],
            preferred_links=["to-b delivery", "workflow orchestration"],
            confidence="medium",
            source_report_ids=["report.business_vertical.llm_agent_rag_engineering.codex_synthesis_2026_04_07"],
            source_model_votes=1,
            freshness_date="2026-04-07",
        ),
        _knowledge_card(
            card_id="role_alias.search_ranking_retrieval_engineering.retrieval_ranking_engineer",
            domain_id="search_ranking_retrieval_engineering",
            report_type="role_family",
            card_type="role_alias",
            title="Retrieval/Ranking Engineer",
            summary="搜索、召回、排序、评估与 candidate ranking 相关工程角色。",
            canonical_terms=["retrieval engineer", "ranking engineer"],
            aliases=["search engineer", "relevance engineer"],
            positive_signals=["retrieval pipeline", "ranking pipeline", "evaluation"],
            negative_signals=["data analyst"],
            query_terms=["retrieval engineer", "ranking", "search"],
            must_have_links=["Python backend", "retrieval or ranking experience"],
            preferred_links=["evaluation", "observability"],
            confidence="high",
            source_report_ids=["report.role_family.search_ranking_retrieval_engineering.codex_synthesis_2026_04_07"],
            source_model_votes=2,
            freshness_date="2026-04-07",
        ),
        _knowledge_card(
            card_id="company_background.search_ranking_retrieval_engineering.search_platform_company",
            domain_id="search_ranking_retrieval_engineering",
            report_type="company_background",
            card_type="company_background",
            title="Search Platform Company Background",
            summary="搜推平台、广告平台、招聘搜索等业务背景。",
            canonical_terms=["search platform", "ranking platform"],
            aliases=["relevance platform", "recommendation platform"],
            positive_signals=["search platform", "ranking platform"],
            negative_signals=["pure operation"],
            query_terms=["search platform", "recommendation", "ranking"],
            must_have_links=["retrieval or ranking experience"],
            preferred_links=["to-b delivery", "observability"],
            confidence="medium",
            source_report_ids=["report.company_background.search_ranking_retrieval_engineering.codex_synthesis_2026_04_07"],
            source_model_votes=1,
            freshness_date="2026-04-07",
        ),
        _knowledge_card(
            card_id="role_alias.finance_risk_control_ai.risk_control_engineer",
            domain_id="finance_risk_control_ai",
            report_type="role_family",
            card_type="role_alias",
            title="Risk Control AI Engineer",
            summary="金融风控、策略引擎与 risk modeling 方向。",
            canonical_terms=["risk control engineer", "risk modeling engineer"],
            aliases=["fraud engineer", "risk strategy engineer"],
            positive_signals=["risk modeling", "feature platform"],
            negative_signals=["marketing analyst"],
            query_terms=["risk control", "fraud", "strategy"],
            must_have_links=["risk modeling", "Python backend"],
            preferred_links=["finance domain"],
            confidence="high",
            source_report_ids=["report.role_family.finance_risk_control_ai.codex_synthesis_2026_04_07"],
            source_model_votes=2,
            freshness_date="2026-04-07",
        ),
    )
    snapshot = GroundingKnowledgeBaseSnapshot(
        snapshot_id="kb-2026-04-07-v1",
        domain_pack_ids=[
            "llm_agent_rag_engineering",
            "search_ranking_retrieval_engineering",
            "finance_risk_control_ai",
        ],
        compiled_report_ids=[
            "report.role_family.llm_agent_rag_engineering.codex_synthesis_2026_04_07",
            "report.role_family.search_ranking_retrieval_engineering.codex_synthesis_2026_04_07",
            "report.role_family.finance_risk_control_ai.codex_synthesis_2026_04_07",
        ],
        card_ids=[card.card_id for card in knowledge_cards],
        compiled_at="2026-04-07T10:30:00+08:00",
    )
    return BootstrapAssets(
        business_policy_pack=BusinessPolicyPack(
            domain_pack_ids=[],
            fusion_weight_preferences=FusionWeightPreferences(
                rerank=0.55,
                must_have=0.25,
                preferred=0.10,
                risk_penalty=0.10,
            ),
            fit_gate_overrides=FitGateConstraints(),
            stability_policy=StabilityPolicy(
                mode="soft_penalty",
                penalty_weight=1.0,
                confidence_floor=0.6,
                allow_hard_gate=False,
            ),
            explanation_preferences=ExplanationPreferences(
                top_n_for_explanation=5,
                emphasize_business_delivery=True,
            ),
        ),
        knowledge_base_snapshot=snapshot,
        knowledge_cards=knowledge_cards,
        reranker_calibration=RerankerCalibration(
            model_id="mlx-community/Qwen3-Reranker-8B-mxfp8",
            normalization="sigmoid",
            temperature=2.4,
            offset=0.0,
            clip_min=-12,
            clip_max=12,
            calibration_version="2026-04-07-v1",
        ),
        knowledge_retrieval_budget=KnowledgeRetrievalBudget(max_cards=8, max_inferred_domain_packs=2),
        runtime_search_budget=RuntimeSearchBudget(
            initial_round_budget=5,
            default_target_new_candidate_count=10,
            max_target_new_candidate_count=20,
        ),
        operator_catalog=DEFAULT_OPERATOR_CATALOG,
    )


def _knowledge_card(
    *,
    card_id: str,
    domain_id: str,
    report_type: str,
    card_type: str,
    title: str,
    summary: str,
    canonical_terms: list[str],
    aliases: list[str],
    positive_signals: list[str],
    negative_signals: list[str],
    query_terms: list[str],
    must_have_links: list[str],
    preferred_links: list[str],
    confidence: str,
    source_report_ids: list[str],
    source_model_votes: int,
    freshness_date: str,
) -> GroundingKnowledgeCard:
    return GroundingKnowledgeCard(
        card_id=card_id,
        domain_id=domain_id,
        report_type=report_type,
        card_type=card_type,
        title=title,
        summary=summary,
        canonical_terms=canonical_terms,
        aliases=aliases,
        positive_signals=positive_signals,
        negative_signals=negative_signals,
        query_terms=query_terms,
        must_have_links=must_have_links,
        preferred_links=preferred_links,
        confidence=confidence,
        source_report_ids=source_report_ids,
        source_model_votes=source_model_votes,
        freshness_date=freshness_date,
    )


__all__ = ["BootstrapAssets", "DEFAULT_OPERATOR_CATALOG", "default_bootstrap_assets"]
