from clo_intel.classify import classify
from clo_intel.schema import DocumentType, oc_ratio_out_of_range


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
