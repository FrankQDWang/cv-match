from __future__ import annotations

import json
from hashlib import sha1
from typing import Any

from pydantic_ai import Agent, NativeOutput

from seektalent.models import (
    BootstrapKeywordDraft,
    BootstrapRoutingResult,
    DomainKnowledgePack,
    LLMCallAuditSnapshot,
    RequirementExtractionDraft,
    RequirementSheet,
    SearchInputTruth,
)

REQUIREMENT_EXTRACTION_INSTRUCTIONS = """
Extract a strict structured requirement draft from the hiring input.
Only use evidence from the provided job description and hiring notes.
Return structured fields only.
""".strip()

BOOTSTRAP_KEYWORD_GENERATION_INSTRUCTIONS = """
Generate a strict structured bootstrap keyword draft for round-0 search startup.
Use only the provided requirement sheet, routing result, and selected knowledge pack.
Do not invent unsupported domain context.
""".strip()

RETRIES = 0
OUTPUT_RETRIES = 1
STRICT_MODEL_SETTINGS = {
    "allow_text_output": False,
    "allow_image_output": False,
}


def _build_agent(
    output_type: type[RequirementExtractionDraft] | type[BootstrapKeywordDraft],
    *,
    model: Any | None,
) -> Agent:
    return Agent(
        model,
        output_type=NativeOutput(output_type, strict=True),
        retries=RETRIES,
        output_retries=OUTPUT_RETRIES,
        builtin_tools=(),
        toolsets=(),
        system_prompt=(),
        model_settings=STRICT_MODEL_SETTINGS,
    )


def _test_model_output(
    output_type: type[RequirementExtractionDraft] | type[BootstrapKeywordDraft],
    *,
    model: Any | None,
) -> RequirementExtractionDraft | BootstrapKeywordDraft | None:
    if getattr(model, "model_name", None) != "test":
        return None
    payload = getattr(model, "custom_output_args", None)
    if not isinstance(payload, dict):
        raise ValueError("test_model_requires_custom_output_args")
    return output_type.model_validate(payload)


def _audit_snapshot(*, model: Any | None, instructions: str) -> LLMCallAuditSnapshot:
    return LLMCallAuditSnapshot(
        output_mode="NativeOutput(strict=True)",
        retries=RETRIES,
        output_retries=OUTPUT_RETRIES,
        validator_retry_count=0,
        model_name=_model_name(model),
        instruction_id_or_hash=sha1(instructions.encode("utf-8")).hexdigest(),
        message_history_mode="fresh",
        tools_enabled=False,
        model_settings_snapshot={**STRICT_MODEL_SETTINGS, "native_output_strict": True},
    )


def _model_name(model: Any | None) -> str:
    if model is None:
        return "default"
    for attr in ("model_name", "name"):
        value = getattr(model, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    return type(model).__name__


async def request_requirement_extraction_draft(
    input_truth: SearchInputTruth,
    *,
    model: Any | None = None,
) -> tuple[RequirementExtractionDraft, LLMCallAuditSnapshot]:
    test_output = _test_model_output(RequirementExtractionDraft, model=model)
    if test_output is not None:
        return test_output, _audit_snapshot(
            model=model,
            instructions=REQUIREMENT_EXTRACTION_INSTRUCTIONS,
        )
    active_agent = _build_agent(RequirementExtractionDraft, model=model)
    result = await active_agent.run(
        input_truth.model_dump_json(),
        message_history=None,
        instructions=REQUIREMENT_EXTRACTION_INSTRUCTIONS,
        builtin_tools=(),
        toolsets=(),
        infer_name=False,
    )
    return RequirementExtractionDraft.model_validate(result.output), _audit_snapshot(
        model=model,
        instructions=REQUIREMENT_EXTRACTION_INSTRUCTIONS,
    )


async def request_bootstrap_keyword_draft(
    requirement_sheet: RequirementSheet,
    routing_result: BootstrapRoutingResult,
    selected_knowledge_pack: DomainKnowledgePack | None,
    *,
    model: Any | None = None,
) -> tuple[BootstrapKeywordDraft, LLMCallAuditSnapshot]:
    test_output = _test_model_output(BootstrapKeywordDraft, model=model)
    if test_output is not None:
        return test_output, _audit_snapshot(
            model=model,
            instructions=BOOTSTRAP_KEYWORD_GENERATION_INSTRUCTIONS,
        )
    active_agent = _build_agent(BootstrapKeywordDraft, model=model)
    packet = json.dumps(
        {
            "requirement_sheet": requirement_sheet.model_dump(mode="json"),
            "routing_result": routing_result.model_dump(mode="json"),
            "selected_knowledge_pack": (
                None if selected_knowledge_pack is None else selected_knowledge_pack.model_dump(mode="json")
            ),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    result = await active_agent.run(
        packet,
        message_history=None,
        instructions=BOOTSTRAP_KEYWORD_GENERATION_INSTRUCTIONS,
        builtin_tools=(),
        toolsets=(),
        infer_name=False,
    )
    return BootstrapKeywordDraft.model_validate(result.output), _audit_snapshot(
        model=model,
        instructions=BOOTSTRAP_KEYWORD_GENERATION_INSTRUCTIONS,
    )


__all__ = [
    "BOOTSTRAP_KEYWORD_GENERATION_INSTRUCTIONS",
    "REQUIREMENT_EXTRACTION_INSTRUCTIONS",
    "request_bootstrap_keyword_draft",
    "request_requirement_extraction_draft",
]
