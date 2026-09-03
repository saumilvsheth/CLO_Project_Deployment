from clo_intel.sample_book import DEALS, field_specs


def test_sample_book_has_at_least_twenty_deals():
    assert len(DEALS) >= 20
    assert len({deal.id for deal in DEALS}) == len(DEALS)


def test_northbridge_is_first_and_apex_spans_deals():
    assert DEALS[0].id == "northbridge-clo-2024-1"
    apex_deals = [
        deal.series
        for deal in DEALS
        if any(item.name == "Apex Industrial Holdings" for item in deal.obligors)
    ]
    assert len(apex_deals) >= 3
    failed_oc = [deal.series for deal in DEALS if not deal.oc_ab_pass]
    assert "Redrock CLO 2024-3" in failed_oc
    assert len(failed_oc) >= 3


def test_field_specs_are_unique_and_cover_every_document():
    specs = field_specs()
    ids = [spec["id"] for spec in specs]
    assert len(ids) == len(set(ids))
    docs = {spec["document_id"] for spec in specs}
    expected = {deal.term_sheet_id() for deal in DEALS}
    expected |= {deal.credit_memo_id() for deal in DEALS}
    expected |= {deal.report_id() for deal in DEALS}
    assert docs == expected
    assert "deal-name" in ids
    assert "apex-name" in ids
    assert "helios-watch" in ids
