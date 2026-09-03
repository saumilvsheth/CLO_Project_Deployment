"""Schema validation and injection scanning before persist."""

from __future__ import annotations

from clo_intel.schema import ExtractionResult, oc_ratio_out_of_range
from clo_intel.telemetry import LOG

_INJECTION = ("ignore previous instructions", "system prompt", "you are now")


def apply_guardrails(result: ExtractionResult) -> ExtractionResult:
    warnings = list(result.warnings)
    for field in result.fields:
        blob = f"{field.value} {field.quote}".lower()
        if any(token in blob for token in _INJECTION):
            field.needs_review = True
            field.review_reason = "Possible prompt injection in source text"
            warnings.append(f"{field.id}: flagged for injection review")
        if "oc" in field.id and oc_ratio_out_of_range(field.value):
            field.needs_review = True
            field.review_reason = field.review_reason or "OC ratio failed range check"
            warnings.append(f"{field.id}: OC ratio {field.value} failed range check")
        if field.confidence < 0.5:
            field.needs_review = True
            field.review_reason = field.review_reason or "Low extraction confidence"
    result.warnings = warnings
    if warnings:
        LOG.warning("Guardrails raised %s warning(s)", len(warnings))
    return result
