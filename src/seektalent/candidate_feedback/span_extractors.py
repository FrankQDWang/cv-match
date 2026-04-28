from __future__ import annotations

import unicodedata
from typing import Protocol

from seektalent.candidate_feedback.extraction import extract_surface_term_occurrences
from seektalent.candidate_feedback.span_models import CandidateSpan, SourceField

_LEGACY_REJECTED_CHINESE_FRAGMENTS = {"掌握至少一种", "引擎", "精通", "及主流", "框架"}


def normalize_source_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def validate_candidate_span(source_text: str, span: CandidateSpan) -> str | None:
    if span.start_char < 0 or span.end_char <= span.start_char or span.end_char > len(source_text):
        return "non_extractively_generated_span"

    raw_surface = source_text[span.start_char : span.end_char]
    if normalize_source_text(raw_surface) != normalize_source_text(span.raw_surface):
        return "non_extractively_generated_span"

    return None


class LegacyRegexSpanExtractor:
    def __init__(self, *, schema_version: str = "legacy-regex-v1") -> None:
        self.schema_version = schema_version

    def extract(
        self,
        *,
        resume_id: str,
        source_field: SourceField,
        texts: list[str],
    ) -> list[CandidateSpan]:
        spans: list[CandidateSpan] = []
        seen: set[tuple[str, int, int]] = set()

        for text in texts:
            for surface, start_char, end_char in extract_surface_term_occurrences(text):
                if not _is_legacy_eligible_surface(surface):
                    continue
                key = (surface, start_char, end_char)
                if key in seen:
                    continue
                seen.add(key)
                span = CandidateSpan.build(
                    source_resume_id=resume_id,
                    source_field=source_field,
                    start_char=start_char,
                    end_char=end_char,
                    raw_surface=surface,
                    normalized_surface=normalize_source_text(surface),
                    model_label="legacy_regex_surface",
                    model_score=1.0,
                    extractor_schema_version=self.schema_version,
                )
                reject_reason = validate_candidate_span(text, span)
                if reject_reason is None:
                    spans.append(span)

        return spans


class SpanModelBackend(Protocol):
    def extract(self, *, text: str, labels: list[str]) -> list[dict[str, object]]: ...


class FakeSpanModelBackend:
    def __init__(self, outputs: list[dict[str, object]]) -> None:
        self.outputs = outputs

    def extract(self, *, text: str, labels: list[str]) -> list[dict[str, object]]:
        return list(self.outputs)


class GLiNER2SpanExtractor:
    def __init__(
        self,
        *,
        backend: SpanModelBackend,
        schema_version: str,
        labels: list[str] | None = None,
    ) -> None:
        self.backend = backend
        self.schema_version = schema_version
        self.labels = list(labels or [])

    def extract(
        self,
        *,
        resume_id: str,
        source_field: SourceField,
        texts: list[str],
    ) -> list[CandidateSpan]:
        spans: list[CandidateSpan] = []

        for text in texts:
            used_offsets: set[tuple[int, int]] = set()
            outputs = self.backend.extract(text=text, labels=self.labels)
            for row in outputs:
                surface = str(row.get("surface", "")).strip()
                label = str(row.get("label", "unknown"))
                score = float(row.get("score", 1.0))
                occurrence = _find_leftmost_unused_occurrence(text, surface, used_offsets)
                if occurrence is None:
                    continue

                start_char, end_char = occurrence
                span = CandidateSpan.build(
                    source_resume_id=resume_id,
                    source_field=source_field,
                    start_char=start_char,
                    end_char=end_char,
                    raw_surface=surface,
                    normalized_surface=normalize_source_text(surface),
                    model_label=label,
                    model_score=score,
                    extractor_schema_version=self.schema_version,
                )
                reject_reason = validate_candidate_span(text, span)
                if reject_reason is not None:
                    continue

                used_offsets.add(occurrence)
                spans.append(span)

        return spans


def _is_legacy_eligible_surface(surface: str) -> bool:
    return surface not in _LEGACY_REJECTED_CHINESE_FRAGMENTS


def _find_leftmost_unused_occurrence(
    text: str,
    surface: str,
    used_offsets: set[tuple[int, int]],
) -> tuple[int, int] | None:
    if not surface:
        return None

    start_char = text.find(surface)
    while start_char != -1:
        # Deterministic rule for ambiguous repeats: keep the first unused match.
        occurrence = (start_char, start_char + len(surface))
        if occurrence not in used_offsets:
            return occurrence
        start_char = text.find(surface, start_char + len(surface))
    return None
