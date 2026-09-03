from clo_intel.sample_book import DEALS, deal_field_ids
from clo_intel.waterfall import (
    SAMPLE_SOFR,
    asset_all_in,
    disbursement_for_deal,
    interest_on,
    parse_book_date,
    parse_money,
    payment_dates,
    period_model,
)


def test_payment_dates_include_indenture_payment():
    deal = next(item for item in DEALS if item.id == "redrock-clo-2024-3")
    dates = payment_dates(deal)
    assert parse_book_date(deal.payment_date) in dates
    assert dates[0] > parse_book_date(deal.close)
    assert dates[0].month == 6
    model = disbursement_for_deal(deal.id, extracted={}, reviews={})
    assert 80 <= model["days"] <= 100


def test_northbridge_waterfall_pays_through_to_residual():
    deal = next(item for item in DEALS if item.id == "northbridge-clo-2024-1")
    model = disbursement_for_deal(deal.id, extracted={}, reviews={})
    assert model["redirect"] is False
    assert model["ocPass"] is True
    assert model["residual"] > 0
    kinds = [step["kind"] for step in model["steps"]]
    assert kinds[0] == "interest"
    assert "paydown" not in kinds
    assert kinds[-1] == "residual"
    a = next(note for note in model["notes"] if note["cls"] == "A")
    assert a["due"] == interest_on(parse_money(deal.class_a_par), SAMPLE_SOFR + 0.0145, model["days"])
    assert model["collected"] == interest_on(parse_money(deal.target_par), asset_all_in(), model["days"])


def test_redrock_failed_oc_redirects_remaining_interest():
    model = disbursement_for_deal("redrock-clo-2024-3", extracted={}, reviews={})
    assert model["ocPass"] is False
    assert model["redirect"] is True
    paydown = next(step for step in model["steps"] if step["kind"] == "paydown")
    assert paydown["paid"] > 0
    class_c = next(step for step in model["steps"] if step["label"].startswith("Class C"))
    assert class_c["paid"] == 0
    assert class_c["deferred"] == class_c["due"]
    assert model["residual"] == 0


def test_hitl_class_a_par_changes_interest_due():
    deal = next(item for item in DEALS if item.id == "northbridge-clo-2024-1")
    field_id = deal_field_ids(deal)["class_a_par"]
    model = disbursement_for_deal(
        deal.id,
        extracted={},
        reviews={field_id: {"status": "overridden", "value": "$100,000,000"}},
    )
    a = next(note for note in model["notes"] if note["cls"] == "A")
    assert a["par"] == 100_000_000
    assert a["due"] == interest_on(100_000_000, SAMPLE_SOFR + 0.0145, model["days"])


def test_period_model_uses_actual_360():
    deal = DEALS[0]
    pay = parse_book_date(deal.payment_date)
    model = period_model(deal, pay, extracted={}, reviews={})
    assert model["dayCount"] == 360
    assert "SOFR" in model["formula"]
    assert model["isReportPeriod"] is True
