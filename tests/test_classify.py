from clo_intel.classify import classify
from clo_intel.contextualize import citation_confidence
from clo_intel.schema import BBox, Citation, DocumentType, oc_ratio_out_of_range


def test_classifies_by_filename():
    assert classify("", "northbridge-clo-2024-1-term-sheet.pdf") == DocumentType.term_sheet
    assert classify("", "northbridge-clo-2024-1-apex-credit-memo.pdf") == DocumentType.credit_memo
    assert classify("", "northbridge-clo-2024-1-monthly-report-aug-2024.pdf") == DocumentType.trustee_report


def test_classifies_trustee_heading():
    assert classify("Monthly report to noteholders.", "unknown.pdf") == DocumentType.trustee_report


def test_oc_ratio_range():
    assert oc_ratio_out_of_range("122.5%") is False
    assert oc_ratio_out_of_range("1900%") is True
    assert oc_ratio_out_of_range("not-a-number") is True


def test_repeated_quote_scores_lower_than_unique():
    box = BBox(x0=0.1, y0=0.1, x1=0.2, y1=0.12)
    unique = [Citation(page=1, quote="$248,000,000", bbox=box)]
    repeated = [Citation(page=1, quote="Apex", bbox=box) for _ in range(8)]
    assert citation_confidence(unique, "$248,000,000") > citation_confidence(repeated, "Apex Industrial Holdings")
    assert citation_confidence([], "missing") < 0.3


def test_classifies_by_filename():
    assert classify("", "northbridge-clo-2024-1-term-sheet.pdf") == DocumentType.term_sheet
    assert classify("", "northbridge-clo-2024-1-apex-credit-memo.pdf") == DocumentType.credit_memo
    assert classify("", "northbridge-clo-2024-1-monthly-report-aug-2024.pdf") == DocumentType.trustee_report


def test_classifies_trustee_heading():
    assert classify("Monthly report to noteholders.", "unknown.pdf") == DocumentType.trustee_report


def test_oc_ratio_range():
    assert oc_ratio_out_of_range("122.5%") is False
    assert oc_ratio_out_of_range("1900%") is True
    assert oc_ratio_out_of_range("not-a-number") is True
