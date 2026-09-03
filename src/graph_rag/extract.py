"""Pull named CLO fields from the sample PDFs, each tied to a citation box."""

from __future__ import annotations

from graph_rag.citations import locate_in_document
from graph_rag.library import get_document

# quote must appear verbatim in the PDF so PyMuPDF can box it.
FIELD_SPECS = [
    {
        "id": "deal-name",
        "label": "Deal name",
        "group": "Parties",
        "documentId": "northbridge-clo-2024-1-term-sheet",
        "quote": "Northbridge CLO 2024-1, Ltd.",
        "value": "Northbridge CLO 2024-1, Ltd.",
    },
    {
        "id": "manager",
        "label": "Collateral manager",
        "group": "Parties",
        "documentId": "northbridge-clo-2024-1-term-sheet",
        "quote": "Meridian Credit Partners LLC",
        "value": "Meridian Credit Partners LLC",
    },
    {
        "id": "trustee",
        "label": "Trustee",
        "group": "Parties",
        "documentId": "northbridge-clo-2024-1-term-sheet",
        "quote": "Harbor Trust Company, N.A.",
        "value": "Harbor Trust Company, N.A.",
    },
    {
        "id": "pm",
        "label": "Portfolio manager",
        "group": "Parties",
        "documentId": "northbridge-clo-2024-1-term-sheet",
        "quote": "Priya Raman",
        "value": "Priya Raman",
    },
    {
        "id": "class-a-par",
        "label": "Class A par",
        "group": "Capital structure",
        "documentId": "northbridge-clo-2024-1-term-sheet",
        "quote": "$248,000,000",
        "value": "$248,000,000",
    },
    {
        "id": "oc-trigger",
        "label": "Class A/B OC trigger",
        "group": "Covenants",
        "documentId": "northbridge-clo-2024-1-term-sheet",
        "quote": "minimum 122.5%",
        "value": "122.5%",
    },
    {
        "id": "apex-name",
        "label": "Obligor",
        "group": "Apex Industrial",
        "documentId": "northbridge-clo-2024-1-apex-credit-memo",
        "quote": "Apex Industrial Holdings",
        "value": "Apex Industrial Holdings",
    },
    {
        "id": "apex-allocation",
        "label": "CLO allocation",
        "group": "Apex Industrial",
        "documentId": "northbridge-clo-2024-1-apex-credit-memo",
        "quote": "$7,200,000",
        "value": "$7,200,000",
    },
    {
        "id": "apex-sponsor",
        "label": "Sponsor",
        "group": "Apex Industrial",
        "documentId": "northbridge-clo-2024-1-apex-credit-memo",
        "quote": "Lakeside Private Equity",
        "value": "Lakeside Private Equity",
    },
    {
        "id": "apex-rating",
        "label": "Moody's rating",
        "group": "Apex Industrial",
        "documentId": "northbridge-clo-2024-1-apex-credit-memo",
        "quote": "Moody's corporate family rating is B1",
        "value": "B1",
    },
    {
        "id": "oc-result",
        "label": "Class A/B OC result",
        "group": "August report",
        "documentId": "northbridge-clo-2024-1-monthly-report-aug-2024",
        "quote": "124.1% vs 122.5% trigger",
        "value": "124.1%",
    },
    {
        "id": "helios-watch",
        "label": "Watchlist name",
        "group": "August report",
        "documentId": "northbridge-clo-2024-1-monthly-report-aug-2024",
        "quote": "Helios Telecom, Inc.",
        "value": "Helios Telecom, Inc.",
    },
]


_CACHE: list[dict] | None = None


def extract_fields() -> list[dict]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    fields = []
    for spec in FIELD_SPECS:
        doc = get_document(spec["documentId"])
        citations = locate_in_document(spec["documentId"], spec["quote"])
        fields.append(
            {
                "id": spec["id"],
                "label": spec["label"],
                "group": spec["group"],
                "documentId": spec["documentId"],
                "documentTitle": doc.title if doc else spec["documentId"],
                "extracted": spec["value"],
                "quote": spec["quote"],
                "citations": citations,
            }
        )
    _CACHE = fields
    return fields
