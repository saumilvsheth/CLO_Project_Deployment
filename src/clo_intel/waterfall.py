"""CLO interest waterfall and payment schedule from the sample-book indenture.

Logic is the language already printed in the term sheets and trustee reports:

- Notes are quarterly SOFR floaters, Actual/360 (term sheet §2).
- Class A–E spreads are SOFR + 1.45% / 2.10% / 2.85% / 4.20% / 7.15%;
  subordinated notes take residual interest.
- Collateral loans earn SOFR + 3.75% with a 0.75% SOFR floor (credit memo §3).
- Failed Class A/B OC or IC redirects remaining interest to pay down Class A,
  then Class B, until the test is cured (term sheet §4 / trustee report §3).
- Failed Interest Diversion Test sends 50% of leftover interest to extra
  collateral or note paydown (term sheet §4).
- After the reinvestment period, principal amortizes sequentially from Class A
  (term sheet §6). Modeled periods do not invent principal collections.
"""

from __future__ import annotations

import calendar
import re
from datetime import date

from clo_intel.review import all_reviews
from clo_intel.sample_book import DEALS, deal_field_ids

# Term sheet §2.
NOTE_SPREADS = (
    ("A", "Class A Senior Secured Floating Rate Notes", 0.0145, False, "AAA(sf)/Aaa(sf)"),
    ("B", "Class B Senior Secured Floating Rate Notes", 0.0210, False, "AA(sf)/Aa2(sf)"),
    ("C", "Class C Mezzanine Secured Deferrable Notes", 0.0285, True, "A(sf)/A2(sf)"),
    ("D", "Class D Mezzanine Secured Deferrable Notes", 0.0420, True, "BBB(sf)/Baa3(sf)"),
    ("E", "Class E Junior Secured Deferrable Notes", 0.0715, True, "BB(sf)/Ba3(sf)"),
)
CLASS_A_WAL_YEARS = 6.8
# Credit memo §3.
ASSET_SPREAD = 0.0375
ASSET_SOFR_FLOOR = 0.0075
# Sample 3-month SOFR. The PDFs do not print a fixing; this is the rate used to
# turn those spreads into dollars.
SAMPLE_SOFR = 0.0535
DAY_COUNT = 360
DIVERSION_SHARE = 0.50

_MONEY = re.compile(r"[-+]?\s*\$?\s*([\d,]+(?:\.\d+)?)")
_MONTHS = {
    name: i
    for i, name in enumerate(
        (
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ),
        start=1,
    )
}


def parse_money(value: str | int | float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    match = _MONEY.search(str(value or ""))
    if not match:
        return 0.0
    return float(match.group(1).replace(",", ""))


def parse_pct(value: str | float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value or "").replace("%", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_book_date(text: str) -> date:
    parts = str(text or "").replace(",", "").split()
    if len(parts) == 3 and parts[1] in _MONTHS:
        return date(int(parts[2]), _MONTHS[parts[1]], int(parts[0]))
    if len(parts) == 1 and "-" in parts[0]:
        y, m, d = parts[0].split("-")
        return date(int(y), int(m), int(d))
    raise ValueError(f"Unrecognized date: {text}")


def format_book_date(value: date) -> str:
    return f"{value.day} {value.strftime('%B')} {value.year}"


def usd(amount: float) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def pct(rate: float) -> str:
    return f"{rate * 100:.2f}%"


def interest_on(par: float, all_in: float, days: int) -> float:
    return round(par * all_in * days / DAY_COUNT, 2)


def asset_all_in(sofr: float = SAMPLE_SOFR) -> float:
    return max(sofr, ASSET_SOFR_FLOOR) + ASSET_SPREAD


def note_all_in(spread: float, sofr: float = SAMPLE_SOFR) -> float:
    return sofr + spread


def _add_months(value: date, months: int) -> date:
    month0 = value.month - 1 + months
    year = value.year + month0 // 12
    month = month0 % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _hitl(field_id: str, fallback: str, extracted: dict, reviews: dict) -> tuple[str, str]:
    review = reviews.get(field_id) or {}
    status = review.get("status", "pending")
    if status in {"approved", "overridden"} and str(review.get("value") or "").strip():
        return str(review["value"]).strip(), status
    if field_id in extracted:
        return extracted[field_id], "extracted"
    return fallback, "sample_book"


def _extracted_values() -> dict[str, str]:
    from clo_intel.store import list_runs, load_run

    values: dict[str, str] = {}
    for row in list_runs():
        run = load_run(row["documentId"])
        if not run:
            continue
        for field in run.get("extraction", {}).get("fields", []):
            values[field["id"]] = field["value"]
    return values


def _oc_pass(trigger: str, result: str, fallback: bool) -> bool:
    try:
        return parse_pct(result) >= parse_pct(trigger)
    except (TypeError, ValueError):
        return fallback


def payment_dates(deal) -> list[date]:
    close = parse_book_date(deal.close)
    pay = parse_book_date(deal.payment_date)
    end = parse_book_date(deal.reinvestment_end)
    cursor = pay
    while _add_months(cursor, -3) > close:
        cursor = _add_months(cursor, -3)
    dates = []
    stop = _add_months(end, 6)
    while cursor <= stop:
        dates.append(cursor)
        cursor = _add_months(cursor, 3)
    if pay not in dates:
        dates.append(pay)
        dates.sort()
    return dates


def _tranche_pars(deal, class_a: float) -> dict[str, float]:
    return {
        "A": class_a,
        "B": parse_money(deal.class_b_par),
        "C": parse_money(deal.class_c_par),
        "D": parse_money(deal.class_d_par),
        "E": parse_money(deal.class_e_par),
        "SUB": parse_money(deal.sub_par),
    }


def period_model(
    deal,
    pay: date,
    *,
    previous: date | None = None,
    sofr: float = SAMPLE_SOFR,
    extracted: dict | None = None,
    reviews: dict | None = None,
) -> dict:
    extracted = extracted if extracted is not None else {}
    reviews = reviews if reviews is not None else {}
    ids = deal_field_ids(deal)
    class_a_raw, class_a_src = _hitl(ids["class_a_par"], deal.class_a_par, extracted, reviews)
    oc_trig, oc_trig_src = _hitl(ids["oc_trigger"], f"{deal.oc_ab_trigger}%", extracted, reviews)
    oc_res, oc_res_src = _hitl(ids["oc_result"], f"{deal.oc_ab_result}%", extracted, reviews)
    start = previous or parse_book_date(deal.close)
    days = max((pay - start).days, 1)
    report_pay = parse_book_date(deal.payment_date)
    is_report = pay == report_pay
    oc_pass = _oc_pass(oc_trig, oc_res, deal.oc_ab_pass) if is_report else True
    ic_pass = deal.ic_ab_pass if is_report else True
    diversion_pass = parse_pct(deal.diversion_result) >= parse_pct(deal.diversion_trigger) if is_report else True
    if not is_report:
        diversion_pass = True
    redirect = not (oc_pass and ic_pass)
    reinvestment_end = parse_book_date(deal.reinvestment_end)
    amortizing = pay > reinvestment_end

    pars = _tranche_pars(deal, parse_money(class_a_raw))
    asset_rate = asset_all_in(sofr)
    collections = []
    collected = 0.0
    named = 0.0
    for obligor in deal.obligors:
        par = parse_money(obligor.allocation)
        named += par
        amount = interest_on(par, asset_rate, days)
        collected += amount
        collections.append(
            {
                "name": obligor.name,
                "par": par,
                "parDisplay": usd(par),
                "amount": amount,
                "amountDisplay": usd(amount),
            }
        )
    other_par = max(parse_money(deal.target_par) - named, 0.0)
    other_int = interest_on(other_par, asset_rate, days)
    collected = round(collected + other_int, 2)
    if other_par:
        collections.append(
            {
                "name": "Other collateral (target par less named obligors)",
                "par": other_par,
                "parDisplay": usd(other_par),
                "amount": other_int,
                "amountDisplay": usd(other_int),
            }
        )

    notes = []
    senior_due = 0.0
    for cls, label, spread, deferrable, rating in NOTE_SPREADS:
        rate = note_all_in(spread, sofr)
        due = interest_on(pars[cls], rate, days)
        if cls in {"A", "B"}:
            senior_due += due
        notes.append(
            {
                "cls": cls,
                "label": label,
                "rating": rating,
                "par": pars[cls],
                "parDisplay": usd(pars[cls]),
                "spread": spread,
                "spreadDisplay": f"SOFR + {spread * 100:.2f}%",
                "allInDisplay": pct(rate),
                "due": due,
                "dueDisplay": usd(due),
                "deferrable": deferrable,
                "wal": CLASS_A_WAL_YEARS if cls == "A" else None,
            }
        )

    modeled_ic = round((collected / senior_due) * 100, 1) if senior_due else 0.0
    available = collected
    steps = []

    def take(label: str, due: float, *, kind: str, deferrable: bool = False) -> float:
        nonlocal available
        paid = round(min(available, due), 2)
        available = round(available - paid, 2)
        unpaid = round(due - paid, 2)
        deferred = unpaid if deferrable else 0.0
        shortfall = 0.0 if deferrable else unpaid
        steps.append(
            {
                "label": label,
                "kind": kind,
                "due": due,
                "dueDisplay": usd(due),
                "paid": paid,
                "paidDisplay": usd(paid),
                "deferred": deferred,
                "deferredDisplay": usd(deferred) if deferred else "",
                "shortfall": shortfall,
                "shortfallDisplay": usd(shortfall) if shortfall else "",
            }
        )
        return paid

    take("Class A interest", notes[0]["due"], kind="interest")
    take("Class B interest", notes[1]["due"], kind="interest")
    paydown = 0.0
    if redirect:
        paydown = available
        take("Class A principal (coverage-test redirect)", paydown, kind="paydown")
        available = 0.0
        for note in notes[2:]:
            take(f"Class {note['cls']} interest", note["due"], kind="interest", deferrable=True)
    else:
        take("Class C interest", notes[2]["due"], kind="interest", deferrable=True)
        take("Class D interest", notes[3]["due"], kind="interest", deferrable=True)
        take("Class E interest", notes[4]["due"], kind="interest", deferrable=True)

    diverted = 0.0
    if not diversion_pass and available:
        diverted = round(available * DIVERSION_SHARE, 2)
        take("Interest diversion (50% to collateral or note paydown)", diverted, kind="diversion")

    residual = available
    take("Subordinated notes (residual interest)", residual, kind="residual")

    formula = (
        f"Interest = par × (rate) × {days}/{DAY_COUNT}. "
        f"Note rate = SOFR + spread. Loan rate = max(SOFR, {pct(ASSET_SOFR_FLOOR)}) + {pct(ASSET_SPREAD)}."
    )
    return {
        "dealId": deal.id,
        "series": deal.series,
        "issuer": deal.issuer,
        "paymentDate": pay.isoformat(),
        "paymentDateDisplay": format_book_date(pay),
        "periodStart": start.isoformat(),
        "periodStartDisplay": format_book_date(start),
        "days": days,
        "dayCount": DAY_COUNT,
        "sofr": sofr,
        "sofrDisplay": pct(sofr),
        "assetRateDisplay": pct(asset_rate),
        "trustee": deal.trustee,
        "manager": deal.manager,
        "close": deal.close,
        "determination": deal.determination if is_report else "",
        "reinvestmentEnd": deal.reinvestment_end,
        "isReportPeriod": is_report,
        "amortizing": amortizing,
        "redirect": redirect,
        "ocPass": oc_pass,
        "icPass": ic_pass,
        "diversionPass": diversion_pass,
        "ocTrigger": oc_trig,
        "ocResult": oc_res,
        "ocSource": oc_res_src,
        "icTrigger": f"{deal.ic_ab_trigger}%",
        "icResult": f"{deal.ic_ab_result}%",
        "modeledIc": modeled_ic,
        "modeledIcDisplay": f"{modeled_ic}%",
        "classASource": class_a_src,
        "collected": collected,
        "collectedDisplay": usd(collected),
        "seniorDue": round(senior_due, 2),
        "seniorDueDisplay": usd(senior_due),
        "paydown": paydown,
        "paydownDisplay": usd(paydown),
        "diverted": diverted,
        "divertedDisplay": usd(diverted),
        "residual": residual,
        "residualDisplay": usd(residual),
        "formula": formula,
        "notes": notes,
        "collections": collections,
        "steps": steps,
        "targetPar": deal.target_par,
    }


def disbursement_for_deal(
    deal_id: str,
    pay: str = "",
    *,
    extracted: dict | None = None,
    reviews: dict | None = None,
    with_schedule: bool = True,
) -> dict:
    deal = next((item for item in DEALS if item.id == deal_id), None)
    if not deal:
        raise ValueError(f"Unknown deal: {deal_id}")
    extracted = extracted if extracted is not None else _extracted_values()
    reviews = reviews if reviews is not None else all_reviews()
    dates = payment_dates(deal)
    chosen = parse_book_date(pay) if pay else parse_book_date(deal.payment_date)
    if chosen not in dates:
        dates.append(chosen)
        dates.sort()
    previous = None
    for item in dates:
        if item >= chosen:
            break
        previous = item
    model = period_model(deal, chosen, previous=previous, extracted=extracted, reviews=reviews)
    if not with_schedule:
        model["schedule"] = []
        return model
    schedule = []
    prev = None
    for item in dates:
        snap = period_model(deal, item, previous=prev, extracted=extracted, reviews=reviews)
        schedule.append(
            {
                "paymentDate": item.isoformat(),
                "paymentDateDisplay": format_book_date(item),
                "days": snap["days"],
                "collectedDisplay": snap["collectedDisplay"],
                "residualDisplay": snap["residualDisplay"],
                "redirect": snap["redirect"],
                "isReportPeriod": snap["isReportPeriod"],
                "amortizing": snap["amortizing"],
                "selected": item == chosen,
            }
        )
        prev = item
    model["schedule"] = schedule
    return model


def format_waterfall_facts(model: dict, cite: str = "") -> list[str]:
    class_a = next((note for note in model.get("notes") or [] if note["cls"] == "A"), None)
    class_b = next((note for note in model.get("notes") or [] if note["cls"] == "B"), None)
    lines = [
        f"  Payment date: {model['paymentDateDisplay']} ({model['days']} days Actual/{model['dayCount']}, SOFR {model['sofrDisplay']}){cite}",
        f"  Interest collected: {model['collectedDisplay']}",
    ]
    if class_a:
        lines.append(f"  Class A interest due: {class_a['dueDisplay']} ({model.get('classASource', 'sample_book')})")
    if class_b:
        lines.append(f"  Class B interest due: {class_b['dueDisplay']}")
    if model.get("redirect"):
        lines.append(f"  Coverage-test redirect: {model['paydownDisplay']} to Class A principal")
        lines.append("  Class C–E interest: deferred this period")
        lines.append("  Subordinated residual: $0.00")
    else:
        lines.append(f"  Subordinated residual: {model['residualDisplay']}")
    if model.get("ocSource") in {"approved", "overridden"}:
        lines.append(f"  Waterfall OC input: {model['ocResult']} ({model['ocSource']})")
    return lines
