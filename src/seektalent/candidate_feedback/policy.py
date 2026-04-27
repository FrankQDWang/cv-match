from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from seektalent.candidate_feedback.models import FeedbackCandidateExpression
from seektalent.models import unique_strings

PRF_POLICY_VERSION = "prf-policy-v1"
MIN_PRF_SEED_COUNT = 2


class PRFGateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_resume_ids: list[str] = Field(default_factory=list)
    candidate_expressions: list[FeedbackCandidateExpression] = Field(default_factory=list)
    tried_term_family_ids: list[str] = Field(default_factory=list)


class PRFPolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prf_gate_passed: bool
    policy_version: str = PRF_POLICY_VERSION
    seed_resume_ids: list[str] = Field(default_factory=list)
    candidate_expression_count: int = 0
    accepted_expression: str | None = None
    accepted_term_family_id: str | None = None
    reject_reasons: list[str] = Field(default_factory=list)
    evaluated_expressions: list[FeedbackCandidateExpression] = Field(default_factory=list)


def build_prf_policy_decision(policy_input: PRFGateInput) -> PRFPolicyDecision:
    seed_resume_ids = unique_strings(policy_input.seed_resume_ids)
    evaluated_expressions = _evaluate_expressions(
        candidate_expressions=policy_input.candidate_expressions,
        tried_term_family_ids=policy_input.tried_term_family_ids,
    )
    if len(seed_resume_ids) < MIN_PRF_SEED_COUNT:
        return PRFPolicyDecision(
            prf_gate_passed=False,
            seed_resume_ids=seed_resume_ids,
            candidate_expression_count=len(policy_input.candidate_expressions),
            reject_reasons=["insufficient_seed_count"],
            evaluated_expressions=evaluated_expressions,
        )

    accepted = next((item for item in evaluated_expressions if not item.reject_reasons), None)
    if accepted is None:
        return PRFPolicyDecision(
            prf_gate_passed=False,
            seed_resume_ids=seed_resume_ids,
            candidate_expression_count=len(policy_input.candidate_expressions),
            reject_reasons=["no_safe_candidate_expression"],
            evaluated_expressions=evaluated_expressions,
        )

    return PRFPolicyDecision(
        prf_gate_passed=True,
        seed_resume_ids=seed_resume_ids,
        candidate_expression_count=len(policy_input.candidate_expressions),
        accepted_expression=accepted.canonical_expression,
        accepted_term_family_id=accepted.term_family_id,
        evaluated_expressions=evaluated_expressions,
    )


def _evaluate_expressions(
    *,
    candidate_expressions: list[FeedbackCandidateExpression],
    tried_term_family_ids: list[str],
) -> list[FeedbackCandidateExpression]:
    tried_families = set(tried_term_family_ids)
    evaluated: list[FeedbackCandidateExpression] = []
    for expression in candidate_expressions:
        reject_reasons = list(expression.reject_reasons)
        if expression.candidate_term_type == "company_entity" and "company_entity" not in reject_reasons:
            reject_reasons.append("company_entity")
        if expression.term_family_id in tried_families and "tried_term_family" not in reject_reasons:
            reject_reasons.append("tried_term_family")
        if (
            expression.negative_support_count > 0
            and expression.negative_support_count >= expression.positive_seed_support_count
            and "negative_support_too_high" not in reject_reasons
        ):
            reject_reasons.append("negative_support_too_high")
        evaluated.append(expression.model_copy(update={"reject_reasons": unique_strings(reject_reasons)}))
    return evaluated
