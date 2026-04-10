from __future__ import annotations

from seektalent.models import (
    FrontierNode_t,
    RequirementSheet,
    RuntimeBudgetState,
    SearchControllerContext_t,
    SearchExecutionPlan_t,
    SearchExecutionResult_t,
    SearchScoringResult_t,
)


def render_controller_context_text(context: SearchControllerContext_t) -> str:
    sections = [
        _section(
            "Task Contract",
            [
                "Use only the provided controller context.",
                "Pick a legal operator from allowed_operator_names.",
                "Do not invent unsupported operators or donor ids outside the provided candidate list.",
            ],
        ),
        _section(
            "Role Summary",
            [
                f"Role title: {context.role_title}",
                f"Role focus: {_or_none(context.role_summary)}",
            ],
        ),
        _section(
            "Active Frontier Node",
            [
                f"Frontier node id: {context.active_frontier_node_summary.frontier_node_id}",
                f"Current operator: {context.active_frontier_node_summary.selected_operator_name}",
                f"Query term pool: {_comma_list(context.active_frontier_node_summary.node_query_term_pool)}",
                f"Current node shortlist ids: {_comma_list(context.active_frontier_node_summary.node_shortlist_candidate_ids)}",
            ],
        ),
        _section("Donor Candidates", _controller_donor_lines(context)),
        _section(
            "Allowed Operators",
            [f"Allowed operators: {_comma_list(context.allowed_operator_names)}"],
        ),
        _section(
            "Operator Statistics",
            _controller_operator_stat_lines(context),
        ),
        _section(
            "Fit Gates And Unmet Requirements",
            _controller_fit_and_requirement_lines(context),
        ),
        _section(
            "Runtime Budget State",
            _controller_budget_lines(context.runtime_budget_state),
        ),
    ]
    if context.runtime_budget_state.near_budget_end:
        sections.append(
            _section(
                "Budget Warning",
                [
                    "The run is in the last 20% of total budget.",
                    "Favor high-yield precision moves.",
                    "Avoid speculative expansion unless must-have coverage is still missing.",
                ],
            )
        )
    sections.append(
        _section(
            "Decision Request",
            [
                "Return a strict structured controller decision draft for the active frontier node.",
            ],
        )
    )
    return "\n\n".join(sections)


def render_branch_evaluation_text(
    requirement_sheet: RequirementSheet,
    parent_node: FrontierNode_t,
    plan: SearchExecutionPlan_t,
    execution_result: SearchExecutionResult_t,
    scoring_result: SearchScoringResult_t,
    runtime_budget_state: RuntimeBudgetState,
) -> str:
    sections = [
        _section(
            "Evaluation Contract",
            [
                "Use only the provided branch evaluation packet.",
                "Do not rewrite runtime facts outside the draft fields.",
            ],
        ),
        _section(
            "Role Summary",
            [
                f"Role title: {requirement_sheet.role_title}",
                f"Role focus: {_or_none(requirement_sheet.role_summary)}",
                f"Must-have capabilities: {_comma_list(requirement_sheet.must_have_capabilities)}",
                f"Preferred capabilities: {_comma_list(requirement_sheet.preferred_capabilities)}",
            ],
        ),
        _section(
            "Branch Facts",
            [
                f"Parent frontier node id: {parent_node.frontier_node_id}",
                f"Previous node shortlist ids: {_comma_list(parent_node.node_shortlist_candidate_ids)}",
                f"Donor frontier node id: {_or_none(plan.child_frontier_node_stub.donor_frontier_node_id)}",
                f"Knowledge pack ids: {_comma_list(plan.knowledge_pack_ids)}",
                f"Query terms: {_comma_list(plan.query_terms)}",
                f"Semantic hash: {plan.semantic_hash}",
            ],
        ),
        _section(
            "Search And Scoring Summary",
            [
                f"Pages fetched: {execution_result.search_page_statistics.pages_fetched}",
                f"Duplicate rate: {execution_result.search_page_statistics.duplicate_rate:.2f}",
                f"Latency ms: {execution_result.search_page_statistics.latency_ms}",
                f"Node shortlist ids: {_comma_list(scoring_result.node_shortlist_candidate_ids)}",
                (
                    "Average fusion score top three: "
                    f"{scoring_result.top_three_statistics.average_fusion_score_top_three:.2f}"
                ),
            ],
        ),
        _section(
            "Runtime Budget State",
            _branch_budget_lines(runtime_budget_state),
        ),
    ]
    if runtime_budget_state.near_budget_end:
        sections.append(
            _section(
                "Budget Warning",
                [
                    "The run is near budget end.",
                    "If incremental upside is weak, be more conservative about keeping the branch open.",
                ],
            )
        )
    sections.append(
        _section(
            "Return Fields",
            [
                "Return novelty_score, usefulness_score, branch_exhausted, repair_operator_hint, and evaluation_notes.",
            ],
        )
    )
    return "\n\n".join(sections)


def _controller_donor_lines(context: SearchControllerContext_t) -> list[str]:
    if not context.donor_candidate_node_summaries:
        return ["No legal donor candidates."]
    return [
        (
            f"{donor.frontier_node_id}: shared_anchor_terms={_comma_list(donor.shared_anchor_terms)}; "
            f"expected_incremental_coverage={_comma_list(donor.expected_incremental_coverage)}; "
            f"reward_score={donor.reward_score:.2f}"
        )
        for donor in context.donor_candidate_node_summaries
    ]


def _controller_operator_stat_lines(context: SearchControllerContext_t) -> list[str]:
    if not context.operator_statistics_summary:
        return ["No operator statistics."]
    ordered_names = list(context.allowed_operator_names) + sorted(
        operator_name
        for operator_name in context.operator_statistics_summary
        if operator_name not in set(context.allowed_operator_names)
    )
    seen: set[str] = set()
    lines: list[str] = []
    for operator_name in ordered_names:
        if operator_name in seen:
            continue
        seen.add(operator_name)
        stats = context.operator_statistics_summary.get(operator_name)
        if stats is None:
            continue
        lines.append(
            f"{operator_name}: average_reward={stats.average_reward:.2f}, times_selected={stats.times_selected}"
        )
    return lines or ["No operator statistics."]


def _controller_fit_and_requirement_lines(context: SearchControllerContext_t) -> list[str]:
    fit_gate_lines = [
        f"Locations: {_comma_list(context.fit_gate_constraints.locations)}",
        f"Min years: {_or_none(context.fit_gate_constraints.min_years)}",
        f"Max years: {_or_none(context.fit_gate_constraints.max_years)}",
        f"Companies: {_comma_list(context.fit_gate_constraints.company_names)}",
        f"Schools: {_comma_list(context.fit_gate_constraints.school_names)}",
        f"Degree requirement: {_or_none(context.fit_gate_constraints.degree_requirement)}",
        f"Gender requirement: {_or_none(context.fit_gate_constraints.gender_requirement)}",
        f"Min age: {_or_none(context.fit_gate_constraints.min_age)}",
        f"Max age: {_or_none(context.fit_gate_constraints.max_age)}",
    ]
    requirement_lines = [
        (
            f"{item.capability}: weight={item.weight:.2f}"
            if isinstance(item.weight, float)
            else f"{item.capability}: weight={item.weight}"
        )
        for item in context.unmet_requirement_weights
    ]
    return fit_gate_lines + ["Unmet requirement weights:"] + (
        requirement_lines or ["None."]
    )


def _controller_budget_lines(runtime_budget_state: RuntimeBudgetState) -> list[str]:
    return [
        f"Initial round budget: {runtime_budget_state.initial_round_budget}",
        f"Runtime round index: {runtime_budget_state.runtime_round_index}",
        f"Remaining budget: {runtime_budget_state.remaining_budget}",
        f"Used ratio: {runtime_budget_state.used_ratio:.2f}",
        f"Remaining ratio: {runtime_budget_state.remaining_ratio:.2f}",
        f"Near budget end: {_bool_text(runtime_budget_state.near_budget_end)}",
    ]


def _branch_budget_lines(runtime_budget_state: RuntimeBudgetState) -> list[str]:
    return [
        f"Runtime round index: {runtime_budget_state.runtime_round_index}",
        f"Remaining budget: {runtime_budget_state.remaining_budget}",
        f"Remaining ratio: {runtime_budget_state.remaining_ratio:.2f}",
        f"Near budget end: {_bool_text(runtime_budget_state.near_budget_end)}",
    ]


def _section(title: str, lines: list[str]) -> str:
    return "\n".join([f"## {title}", *[f"- {line}" for line in lines]])


def _comma_list(values: list[object]) -> str:
    items = [str(value) for value in values if str(value).strip()]
    return ", ".join(items) if items else "None"


def _or_none(value: object) -> str:
    if value is None:
        return "None"
    text = str(value).strip()
    return text or "None"


def _bool_text(value: bool) -> str:
    return "yes" if value else "no"


__all__ = [
    "render_branch_evaluation_text",
    "render_controller_context_text",
]
