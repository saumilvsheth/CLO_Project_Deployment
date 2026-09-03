"""Map raw layout JSON onto the canonical CLO schema, with citations."""

from __future__ import annotations

from pathlib import Path

from clo_intel.extract import locate_quote
from clo_intel.sample_book import field_specs
from clo_intel.schema import ExtractedField, oc_ratio_out_of_range

# quote must appear verbatim in the sample PDFs so bounding boxes can be drawn.
FIELD_SPECS: list[dict] = field_specs()


def citation_confidence(citations: list, quote: str, kind: str | None = None) -> float:
    """Lower score when the quote is missing, short, or repeated across the PDF."""
    if not citations:
        return 0.22
    n = len(citations)
    if n == 1:
        score = 0.94
    elif n <= 3:
        score = 0.82
    else:
        score = 0.64
    if kind == "oc_ratio":
        score = min(score, 0.88)
    if len(quote) < 12:
        score -= 0.08
    return round(max(0.2, min(0.99, score)), 2)


def fields_for_document(document_id: str, pdf_path: Path) -> list[ExtractedField]:
    out: list[ExtractedField] = []
    for spec in FIELD_SPECS:
        if spec["document_id"] != document_id:
            continue
        citations = locate_quote(pdf_path, spec["quote"])
        confidence = citation_confidence(citations, spec["quote"], spec.get("kind"))
        for cite in citations:
            cite.confidence = confidence
        needs_review = False
        reason = ""
        if spec.get("kind") == "oc_ratio" and oc_ratio_out_of_range(spec["value"]):
            needs_review = True
            reason = "OC ratio outside 50–300%"
        if not citations:
            needs_review = True
            reason = "Citation quote not found in PDF"
        out.append(
            ExtractedField(
                id=spec["id"],
                label=spec["label"],
                group=spec["group"],
                value=spec["value"],
                quote=spec["quote"],
                kind=spec.get("kind") or "",
                citations=citations,
                needs_review=needs_review,
                review_reason=reason,
            )
        )
    out.sort(key=lambda field: field.confidence)
    return out
