"""Map raw layout JSON onto the canonical CLO schema, with citations."""

from __future__ import annotations

from pathlib import Path

from clo_intel.extract import locate_quote
from clo_intel.schema import ExtractedField, oc_ratio_out_of_range

# quote must appear verbatim in the sample PDFs so bounding boxes can be drawn.
FIELD_SPECS: list[dict] = [
    {
        "id": "deal-name",
        "label": "Deal name",
        "group": "Parties",
        "document_id": "northbridge-clo-2024-1-term-sheet",
        "quote": "Northbridge CLO 2024-1, Ltd.",
        "value": "Northbridge CLO 2024-1, Ltd.",
    },
    {
        "id": "manager",
        "label": "Collateral manager",
        "group": "Parties",
        "document_id": "northbridge-clo-2024-1-term-sheet",
        "quote": "Meridian Credit Partners LLC",
        "value": "Meridian Credit Partners LLC",
    },
    {
        "id": "trustee",
        "label": "Trustee",
        "group": "Parties",
        "document_id": "northbridge-clo-2024-1-term-sheet",
        "quote": "Harbor Trust Company, N.A.",
        "value": "Harbor Trust Company, N.A.",
    },
    {
        "id": "pm",
        "label": "Portfolio manager",
        "group": "Parties",
        "document_id": "northbridge-clo-2024-1-term-sheet",
        "quote": "Priya Raman",
        "value": "Priya Raman",
    },
    {
        "id": "class-a-par",
        "label": "Class A par",
        "group": "Capital structure",
        "document_id": "northbridge-clo-2024-1-term-sheet",
        "quote": "$248,000,000",
        "value": "$248,000,000",
    },
    {
        "id": "oc-trigger",
        "label": "Class A/B OC trigger",
        "group": "Covenants",
        "document_id": "northbridge-clo-2024-1-term-sheet",
        "quote": "minimum 122.5%",
        "value": "122.5%",
        "kind": "oc_ratio",
    },
    {
        "id": "apex-name",
        "label": "Obligor",
        "group": "Apex Industrial",
        "document_id": "northbridge-clo-2024-1-apex-credit-memo",
        "quote": "Apex Industrial Holdings",
        "value": "Apex Industrial Holdings",
    },
    {
        "id": "apex-allocation",
        "label": "CLO allocation",
        "group": "Apex Industrial",
        "document_id": "northbridge-clo-2024-1-apex-credit-memo",
        "quote": "$7,200,000",
        "value": "$7,200,000",
    },
    {
        "id": "apex-sponsor",
        "label": "Sponsor",
        "group": "Apex Industrial",
        "document_id": "northbridge-clo-2024-1-apex-credit-memo",
        "quote": "Lakeside Private Equity",
        "value": "Lakeside Private Equity",
    },
    {
        "id": "apex-rating",
        "label": "Moody's rating",
        "group": "Apex Industrial",
        "document_id": "northbridge-clo-2024-1-apex-credit-memo",
        "quote": "Moody's corporate family rating is B1",
        "value": "B1",
    },
    {
        "id": "oc-result",
        "label": "Class A/B OC result",
        "group": "August report",
        "document_id": "northbridge-clo-2024-1-monthly-report-aug-2024",
        "quote": "124.1% vs 122.5% trigger",
        "value": "124.1%",
        "kind": "oc_ratio",
    },
    {
        "id": "helios-watch",
        "label": "Watchlist name",
        "group": "August report",
        "document_id": "northbridge-clo-2024-1-monthly-report-aug-2024",
        "quote": "Helios Telecom, Inc.",
        "value": "Helios Telecom, Inc.",
    },
]


def fields_for_document(document_id: str, pdf_path: Path) -> list[ExtractedField]:
    out: list[ExtractedField] = []
    for spec in FIELD_SPECS:
        if spec["document_id"] != document_id:
            continue
        citations = locate_quote(pdf_path, spec["quote"])
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
                confidence=1.0 if citations else 0.2,
                citations=citations,
                needs_review=needs_review,
                review_reason=reason,
            )
        )
    return out
