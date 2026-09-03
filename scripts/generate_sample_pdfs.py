"""Build fictional CLO sample PDFs from the shared sample book.

Run from the repo root:

    .venv/bin/python scripts/generate_sample_pdfs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from clo_intel.sample_book import DEALS, Deal  # noqa: E402

OUTPUT_DIR = ROOT / "data" / "pdfs"


class CloPdf(FPDF):
    """Simple text PDF with a header, footer, and wrapped paragraphs."""

    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__()
        self.doc_title = title
        self.doc_subtitle = subtitle
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(18, 18, 18)

    def header(self) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 11)
        self.multi_cell(0, 6, self.doc_title)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(80, 80, 80)
        self.set_x(self.l_margin)
        self.multi_cell(0, 5, self.doc_subtitle)
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(90, 90, 90)
        self.cell(
            0,
            8,
            f"FICTIONAL SAMPLE  |  Not a real offering  |  Page {self.page_no()}",
            align="C",
        )

    def heading(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.multi_cell(0, 7, text)
        self.ln(1)

    def body(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet(self, text: str) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, f"- {text}")


def _write(pdf: CloPdf, filename: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    pdf.output(path)
    return path


def _pass_fail(ok: bool) -> str:
    return "Pass" if ok else "Fail"


def build_term_sheet(deal: Deal) -> Path:
    pdf = CloPdf(
        deal.issuer,
        f"Preliminary Term Sheet  |  {deal.term_sheet_date}  |  Confidential",
    )
    pdf.add_page()
    pdf.heading("1. Transaction overview")
    pdf.body(
        f"This preliminary term sheet describes {deal.issuer}, "
        f"a Cayman Islands exempted company (the Issuer), and {deal.co_issuer}, "
        "a Delaware limited liability company (the Co-Issuer). The Issuers will issue "
        "secured notes and subordinated notes in a collateralized loan obligation "
        f"managed by {deal.manager} (the Collateral Manager). "
        f"{deal.trustee} will act as Trustee, collateral administrator, "
        "and notes paying agent. The transaction is expected to close on "
        f"{deal.close} in {deal.manager_city}. This document is a fictional sample "
        "for software testing only and is not an offer to sell securities."
    )
    pdf.body(
        f"{deal.pm} is the lead portfolio manager at {deal.manager} "
        f"for {deal.series}. {deal.cco} is the chief credit officer. "
        f"The Collateral Manager is headquartered in {deal.manager_city} and is a "
        f"wholly owned subsidiary of {deal.manager_parent}."
    )
    pdf.heading("2. Capital structure")
    pdf.body(
        "The Issuers expect to issue the following tranches. Par amounts are in "
        "US dollars. Ratings are expected ratings from Moody's and S&P and are not "
        "a recommendation to buy."
    )
    for line in (
        f"Class A Senior Secured Floating Rate Notes: {deal.class_a_par}; AAA(sf)/Aaa(sf); "
        "SOFR + 1.45%; WAL 6.8 years.",
        f"Class B Senior Secured Floating Rate Notes: {deal.class_b_par}; AA(sf)/Aa2(sf); "
        "SOFR + 2.10%.",
        f"Class C Mezzanine Secured Deferrable Notes: {deal.class_c_par}; A(sf)/A2(sf); "
        "SOFR + 2.85%.",
        f"Class D Mezzanine Secured Deferrable Notes: {deal.class_d_par}; BBB(sf)/Baa3(sf); "
        "SOFR + 4.20%.",
        f"Class E Junior Secured Deferrable Notes: {deal.class_e_par}; BB(sf)/Ba3(sf); "
        "SOFR + 7.15%.",
        f"Subordinated Notes: {deal.sub_par}; unrated; residual interest.",
    ):
        pdf.bullet(line)
    pdf.heading("3. Collateral and eligibility")
    pdf.body(
        "The portfolio will consist primarily of US broadly syndicated first-lien "
        f"senior secured loans, with a target par amount of {deal.target_par}. At closing, "
        f"the warehouse facility provided by {deal.warehouse} will be refinanced into "
        "the CLO. Eligible collateral must be US dollar denominated, have a Moody's "
        "rating of at least Caa1 or an S&P rating of at least CCC+, and may not be "
        "equity, bonds, or delayed-draw commitments above the stated basket."
    )
    seeds = ", ".join(
        f"{item.name} ({item.instrument})" for item in deal.obligors[:4]
    )
    pdf.body(
        f"Initial seed names expected in the warehouse include {seeds}. "
        f"{deal.primary.name} is sponsored by {deal.primary.sponsor}."
    )
    pdf.add_page()
    pdf.heading("4. Coverage tests and covenants")
    pdf.body(
        f"{deal.series} will be governed by standard overcollateralization "
        "and interest coverage tests. Failure of a Class A/B Overcollateralization Test "
        "or a Class A/B Interest Coverage Test redirects interest proceeds to pay "
        "down senior notes in sequential order until the test is cured."
    )
    pdf.bullet(
        f"Class A/B Overcollateralization Test: minimum {deal.oc_ab_trigger}%. This covenant is "
        f"measured monthly by {deal.trustee} as Trustee."
    )
    pdf.bullet(f"Class A/B Interest Coverage Test: minimum {deal.ic_ab_trigger}%.")
    pdf.bullet(f"Class C Overcollateralization Test: minimum {deal.oc_c_trigger}%.")
    pdf.bullet(f"Class D Overcollateralization Test: minimum {deal.oc_d_trigger}%.")
    pdf.bullet(
        f"Interest Diversion Test: if the Class E par coverage ratio is below {deal.diversion_trigger}%, "
        "50% of remaining interest is used to buy additional collateral or pay down notes."
    )
    pdf.heading("5. Concentration limits")
    pdf.body(
        "The indenture imposes the following concentration limits on the collateral "
        "principal amount. Excess amounts are treated as haircut collateral for tests."
    )
    pdf.bullet(
        f"Largest obligor: 2.0% ({deal.primary.name} is expected near {deal.primary.pct}% at close)."
    )
    pdf.bullet("Largest Moody's industry: 12.0%.")
    pdf.bullet("Caa bucket (Moody's Caa1 or below): 7.5%.")
    pdf.bullet("Second-lien and unsecured loans: 5.0% combined.")
    pdf.bullet("Covenant-lite loans: 90.0% maximum.")
    pdf.bullet("Non-US obligors: 15.0% maximum.")
    pdf.heading("6. Parties and contacts")
    pdf.body(
        f"Collateral Manager: {deal.manager}, {deal.manager_city}. "
        f"Primary coverage: {deal.pm} (portfolio manager) and {deal.cco} "
        f"(chief credit officer). Trustee and collateral administrator: {deal.trustee}, "
        f"{deal.trustee_city}. Placement agent: {deal.placement}. "
        f"Warehouse lender: {deal.warehouse}. Issuer counsel: {deal.counsel}. "
        f"Questions on this term sheet should be directed to {deal.pm} at {deal.manager}."
    )
    pdf.body(
        f"The Collateral Manager may sell or buy loans for {deal.series} "
        "during the five-year reinvestment period, subject to the eligibility criteria "
        "and the reinvestment overcollateralization test. After the reinvestment "
        f"period ends on {deal.reinvestment_end}, principal proceeds are used to amortize "
        "the notes sequentially, beginning with the Class A Senior Secured Floating "
        "Rate Notes."
    )
    return _write(pdf, f"{deal.term_sheet_id()}.pdf")


def build_credit_memo(deal: Deal) -> Path:
    name = deal.primary
    pdf = CloPdf(
        "Investment Credit Memorandum",
        f"{deal.series}  |  {name.name}  |  {deal.memo_date}",
    )
    pdf.add_page()
    pdf.heading("1. Recommendation")
    pdf.body(
        f"Credit committee is asked to approve a {name.allocation} allocation of the "
        f"{name.name} {name.instrument} into the {deal.series} "
        "warehouse, and to roll that position into the CLO at closing. The borrower "
        f"is {name.name}, headquartered in {name.city}. "
        f"The financial sponsor is {name.sponsor}. Analyst: {deal.analyst}. "
        f"Committee chair: {deal.cco}. Portfolio manager: {deal.pm}, {deal.manager}."
    )
    pdf.body(
        f"Recommendation: Approve at a maximum par of {name.allocation} ({name.pct}% of the "
        f"{deal.target_par} target CLO portfolio). The name sits inside the 2.0% single "
        f"obligor concentration limit in the {deal.series} indenture. "
        f"Moody's corporate family rating is {name.moodys}. S&P issuer credit rating is {name.sp}. "
        "The loan is US dollar denominated and is eligible collateral under the term sheet "
        f"dated {deal.term_sheet_date}."
    )
    pdf.heading("2. Borrower and sponsor")
    pdf.body(
        f"{name.name} operates in {name.industry}. The company is owned by "
        f"{name.sponsor}. Neither the sponsor nor the borrower is affiliated with "
        f"{deal.manager}."
    )
    others = [item.name for item in deal.obligors[1:3]]
    if others:
        pdf.body(
            f"Related book names in {deal.series} include {', '.join(others)}. "
            "Those names are separate obligors and should not be aggregated for the "
            "single obligor test."
        )
    pdf.heading("3. Facility terms")
    pdf.body(
        f"Instrument: {name.name} {name.instrument}. Spread: SOFR + 3.75% with a "
        "0.75% floor. The credit agreement is covenant-lite. "
        f"{deal.warehouse} is the warehouse lender to {deal.series}."
    )
    pdf.add_page()
    pdf.heading("4. Credit highlights and risks")
    pdf.body(
        f"Highlights: sponsor support from {name.sponsor}, first-lien or unitranche "
        "collateral, and an allocation inside the 2.0% obligor cap."
    )
    pdf.body(
        f"Risks: sector cyclicality in {name.industry} and add-on acquisition risk. "
        f"{deal.analyst} confirmed that Moody's industry classification for "
        f"{name.name} is '{name.industry}'."
    )
    pdf.heading("5. CLO fit and covenants")
    pdf.body(
        "The allocation complies with the Class A/B Overcollateralization Test "
        f"methodology because the loan is par-eligible and rated {name.moodys}. "
        f"It uses {name.pct} of the 2.00 percentage-point largest-obligor covenant. "
        f"{deal.pm} confirmed the trade for {deal.series}."
    )
    pdf.body(
        f"If {name.name} is downgraded to Caa1, the position would count toward "
        f"the 7.5% Caa bucket in the {deal.series} indenture. {deal.trustee} would "
        f"reflect that classification on the next monthly trustee report. {deal.manager} "
        "would then evaluate a sale during the reinvestment period."
    )
    pdf.heading("6. Committee decision")
    pdf.body(
        f"Credit committee of {deal.manager} approved the {name.allocation} "
        f"purchase for the {deal.series} warehouse on {deal.memo_date}. "
        f"Voting members: {deal.cco} (chair), {deal.pm}, and {deal.analyst}. "
        f"The trade will settle into the {deal.warehouse} warehouse and be conveyed "
        f"to {deal.issuer} on the closing date of {deal.close}."
    )
    return _write(pdf, f"{deal.credit_memo_id()}.pdf")


def build_monthly_report(deal: Deal) -> Path:
    pdf = CloPdf(
        "Monthly Trustee Report",
        f"{deal.series}  |  Report date {deal.report_date}  |  Determination {deal.determination}",
    )
    pdf.add_page()
    pdf.heading("1. Report identification")
    pdf.body(
        f"{deal.trustee}, as Trustee and collateral administrator for "
        f"{deal.issuer} and {deal.co_issuer}, delivers "
        f"this monthly report to noteholders. Collateral Manager: {deal.manager}. "
        f"Portfolio manager: {deal.pm}. Payment date: {deal.payment_date}. "
        "This report is a fictional sample for software testing and does not describe "
        "a live securitization."
    )
    pdf.heading("2. Capital structure outstanding")
    pdf.body(
        "Outstanding note balances as of the determination date are unchanged from "
        f"closing except for a modest unscheduled paydown on the Class A Senior Secured "
        f"Floating Rate Notes. Subordinated Notes remain {deal.sub_par}. The Trustee "
        "confirms the interest waterfalls described below."
    )
    pdf.heading("3. Coverage test results")
    if deal.oc_ab_pass and deal.ic_ab_pass:
        pdf.body(
            f"All coverage tests passed on the determination date. {deal.trustee} "
            "calculated the ratios below using the indenture definitions. No "
            "redirection of interest proceeds is required this period."
        )
    else:
        pdf.body(
            f"One or more coverage tests failed on the determination date. {deal.trustee} "
            "calculated the ratios below using the indenture definitions. Interest "
            "proceeds are redirected to pay down senior notes until the failed test is cured."
        )
    pdf.bullet(
        f"Class A/B Overcollateralization Test: {deal.oc_ab_result}% vs {deal.oc_ab_trigger}% trigger. "
        f"{_pass_fail(deal.oc_ab_pass)}."
    )
    pdf.bullet(
        f"Class A/B Interest Coverage Test: {deal.ic_ab_result}% vs {deal.ic_ab_trigger}% trigger. "
        f"{_pass_fail(deal.ic_ab_pass)}."
    )
    pdf.bullet(
        f"Class C Overcollateralization Test: {deal.oc_c_result}% vs {deal.oc_c_trigger}% trigger. "
        f"{_pass_fail(deal.oc_ab_pass)}."
    )
    pdf.bullet(
        f"Class D Overcollateralization Test: {deal.oc_d_result}% vs {deal.oc_d_trigger}% trigger. "
        f"{_pass_fail(deal.oc_ab_pass)}."
    )
    pdf.bullet(
        f"Interest Diversion Test (Class E par coverage): {deal.diversion_result}% vs {deal.diversion_trigger}%. "
        f"{_pass_fail(deal.oc_ab_pass)}."
    )
    pdf.heading("4. Largest obligors")
    pdf.body(
        "The five largest obligors as a percentage of collateral principal amount "
        "are listed below. The largest-obligor concentration limit remains 2.0%."
    )
    for item in deal.obligors:
        watch_note = " On watch." if item.watch else " No watch."
        pdf.bullet(
            f"{item.name}: {item.pct}%. {item.instrument.capitalize()}. Sponsor: {item.sponsor}. "
            f"Rating {item.moodys}/{item.sp}. {item.city}.{watch_note}"
        )
    pdf.add_page()
    pdf.heading("5. Watchlist and trading")
    watched = [item for item in deal.obligors if item.watch]
    if watched:
        names = ", ".join(item.name for item in watched)
        pdf.body(
            f"{deal.pm} of {deal.manager} advised the Trustee that "
            f"{names} {'is' if len(watched) == 1 else 'are'} on the official watchlist. "
            f"{deal.cco}, chief credit officer, authorized a sale during the reinvestment "
            "period if bids are at or above 97.00. No sale settled in this period."
        )
    else:
        pdf.body(
            f"{deal.pm} of {deal.manager} advised the Trustee that "
            "no names are on the official watchlist. Performing names were left unchanged "
            "this period."
        )
    extra = deal.obligors[-1] if len(deal.obligors) > 1 else deal.primary
    pdf.body(
        f"Reinvestment: {deal.manager} purchased additional par of "
        f"{extra.name} {extra.instrument} during the period. The loan "
        "is eligible collateral and US dollar denominated. The trade "
        "complies with the Class A/B Overcollateralization Test and the 2.0% "
        f"obligor limit. {deal.trustee} settled the purchase into the custodial account."
    )
    pdf.heading("6. Concentration and Caa bucket")
    pdf.body(
        f"Caa bucket (Moody's Caa1 or below): {deal.caa_pct}% versus a 7.5% limit. "
        f"Largest Moody's industry includes {deal.primary.industry} exposure from "
        f"{deal.primary.name} and is below the 12.0% industry limit."
    )
    pdf.heading("7. Notices")
    pdf.body(
        f"Noteholders with questions should contact {deal.trustee} "
        f"in {deal.trustee_city}, or the Collateral Manager, {deal.manager}, "
        f"in {deal.manager_city}. {deal.series} remains in its reinvestment period "
        f"until {deal.reinvestment_end}. This report should be read with the "
        f"{deal.term_sheet_date} term sheet and the {deal.primary.name} credit memorandum "
        f"dated {deal.memo_date}."
    )
    return _write(pdf, f"{deal.report_id()}.pdf")


def main() -> None:
    paths: list[Path] = []
    for deal in DEALS:
        paths.extend(
            [
                build_term_sheet(deal),
                build_credit_memo(deal),
                build_monthly_report(deal),
            ]
        )
    for path in paths:
        print(path)
    print(f"{len(DEALS)} deals, {len(paths)} PDFs", file=sys.stderr)


if __name__ == "__main__":
    main()
