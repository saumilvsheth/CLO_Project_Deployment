from __future__ import annotations

from clo_intel.schema import DocumentType


def classify(text: str, filename: str = "") -> DocumentType:
    name = filename.lower()
    if "term-sheet" in name:
        return DocumentType.term_sheet
    if "credit-memo" in name or "credit_memo" in name:
        return DocumentType.credit_memo
    if "monthly-report" in name or "trustee-report" in name:
        return DocumentType.trustee_report
    if "indenture" in name:
        return DocumentType.indenture
    if "offering" in name or "om-" in name:
        return DocumentType.offering_memorandum
    if "rating" in name:
        return DocumentType.rating_report

    blob = text.lower()
    headings = [
        (DocumentType.credit_memo, "credit memorandum"),
        (DocumentType.trustee_report, "monthly report to noteholders"),
        (DocumentType.term_sheet, "preliminary term sheet"),
        (DocumentType.offering_memorandum, "offering memorandum"),
        (DocumentType.indenture, "this indenture"),
        (DocumentType.rating_report, "rating action"),
    ]
    for doc_type, needle in headings:
        if needle in blob:
            return doc_type
    return DocumentType.unknown
