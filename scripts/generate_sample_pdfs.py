"""Build fictional CLO sample PDFs for Graph RAG demos.

Run from the repo root:

    .venv/bin/python scripts/generate_sample_pdfs.py
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "pdfs"


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


def build_term_sheet() -> Path:
    pdf = CloPdf(
        "Northbridge CLO 2024-1, Ltd.",
        "Preliminary Term Sheet  |  12 March 2024  |  Confidential",
    )
    pdf.add_page()
    pdf.heading("1. Transaction overview")
    pdf.body(
        "This preliminary term sheet describes Northbridge CLO 2024-1, Ltd., "
        "a Cayman Islands exempted company (the Issuer), and Northbridge CLO 2024-1, LLC, "
        "a Delaware limited liability company (the Co-Issuer). The Issuers will issue "
        "secured notes and subordinated notes in a collateralized loan obligation "
        "managed by Meridian Credit Partners LLC (the Collateral Manager). "
        "Harbor Trust Company, N.A. will act as Trustee, collateral administrator, "
        "and notes paying agent. The transaction is expected to close on 28 March 2024 "
        "in New York. This document is a fictional sample for software testing only "
        "and is not an offer to sell securities."
    )
    pdf.body(
        "Priya Raman is the lead portfolio manager at Meridian Credit Partners LLC "
        "for Northbridge CLO 2024-1. David Okonkwo is the chief credit officer. "
        "The Collateral Manager is headquartered in New York and is a wholly owned "
        "subsidiary of Meridian Holdings LP."
    )
    pdf.heading("2. Capital structure")
    pdf.body(
        "The Issuers expect to issue the following tranches. Par amounts are in "
        "US dollars. Ratings are expected ratings from Moody's and S&P and are not "
        "a recommendation to buy."
    )
    for line in (
        "Class A Senior Secured Floating Rate Notes: $248,000,000; AAA(sf)/Aaa(sf); "
        "SOFR + 1.45%; WAL 6.8 years.",
        "Class B Senior Secured Floating Rate Notes: $36,000,000; AA(sf)/Aa2(sf); "
        "SOFR + 2.10%.",
        "Class C Mezzanine Secured Deferrable Notes: $24,000,000; A(sf)/A2(sf); "
        "SOFR + 2.85%.",
        "Class D Mezzanine Secured Deferrable Notes: $18,000,000; BBB(sf)/Baa3(sf); "
        "SOFR + 4.20%.",
        "Class E Junior Secured Deferrable Notes: $14,000,000; BB(sf)/Ba3(sf); "
        "SOFR + 7.15%.",
        "Subordinated Notes: $32,000,000; unrated; residual interest.",
    ):
        pdf.bullet(line)
    pdf.heading("3. Collateral and eligibility")
    pdf.body(
        "The portfolio will consist primarily of US broadly syndicated first-lien "
        "senior secured loans, with a target par amount of $400,000,000. At closing, "
        "the warehouse facility provided by Bridgeport Bank will be refinanced into "
        "the CLO. Eligible collateral must be US dollar denominated, have a Moody's "
        "rating of at least Caa1 or an S&P rating of at least CCC+, and may not be "
        "equity, bonds, or delayed-draw commitments above the stated basket."
    )
    pdf.body(
        "Initial seed names expected in the warehouse include Apex Industrial Holdings "
        "(first-lien term loan), Helios Telecom, Inc. (first-lien term loan), "
        "Redwood Packaging LLC (first-lien term loan), and Cascade Health Services "
        "(unitranche). Apex Industrial Holdings is sponsored by Lakeside Private Equity. "
        "Helios Telecom, Inc. is sponsored by Orion Capital Partners."
    )
    pdf.add_page()
    pdf.heading("4. Coverage tests and covenants")
    pdf.body(
        "Northbridge CLO 2024-1 will be governed by standard overcollateralization "
        "and interest coverage tests. Failure of a Class A/B Overcollateralization Test "
        "or a Class A/B Interest Coverage Test redirects interest proceeds to pay "
        "down senior notes in sequential order until the test is cured. The "
        "Class C Overcollateralization Test and Class D Overcollateralization Test "
        "apply further down the capital structure."
    )
    pdf.bullet(
        "Class A/B Overcollateralization Test: minimum 122.5%. This covenant is "
        "measured monthly by Harbor Trust Company, N.A. as Trustee."
    )
    pdf.bullet(
        "Class A/B Interest Coverage Test: minimum 120.0%."
    )
    pdf.bullet(
        "Class C Overcollateralization Test: minimum 114.0%."
    )
    pdf.bullet(
        "Class D Overcollateralization Test: minimum 108.5%."
    )
    pdf.bullet(
        "Interest Diversion Test: if the Class E par coverage ratio is below 104.5%, "
        "50% of remaining interest is used to buy additional collateral or pay down notes."
    )
    pdf.heading("5. Concentration limits")
    pdf.body(
        "The indenture imposes the following concentration limits on the collateral "
        "principal amount. Excess amounts are treated as haircut collateral for tests."
    )
    pdf.bullet("Largest obligor: 2.0% (Apex Industrial Holdings is expected near 1.8% at close).")
    pdf.bullet("Largest Moody's industry: 12.0%.")
    pdf.bullet("Caa bucket (Moody's Caa1 or below): 7.5%.")
    pdf.bullet("Second-lien and unsecured loans: 5.0% combined.")
    pdf.bullet("Covenant-lite loans: 90.0% maximum.")
    pdf.bullet("Non-US obligors: 15.0% maximum.")
    pdf.heading("6. Parties and contacts")
    pdf.body(
        "Collateral Manager: Meridian Credit Partners LLC, 200 Park Avenue, New York. "
        "Primary coverage: Priya Raman (portfolio manager) and David Okonkwo "
        "(chief credit officer). Trustee and collateral administrator: Harbor Trust "
        "Company, N.A., Wilmington. Placement agent: Westfield Securities LLC. "
        "Warehouse lender: Bridgeport Bank. Issuer counsel: Hale & Martin LLP. "
        "Questions on this term sheet should be directed to Priya Raman at "
        "Meridian Credit Partners LLC."
    )
    pdf.body(
        "The Collateral Manager may sell or buy loans for Northbridge CLO 2024-1 "
        "during the five-year reinvestment period, subject to the eligibility criteria "
        "and the reinvestment overcollateralization test. After the reinvestment "
        "period ends on 28 March 2029, principal proceeds are used to amortize "
        "the notes sequentially, beginning with the Class A Senior Secured Floating "
        "Rate Notes."
    )
    return _write(pdf, "northbridge-clo-2024-1-term-sheet.pdf")


def build_credit_memo() -> Path:
    pdf = CloPdf(
        "Investment Credit Memorandum",
        "Northbridge CLO 2024-1  |  Apex Industrial Holdings  |  4 March 2024",
    )
    pdf.add_page()
    pdf.heading("1. Recommendation")
    pdf.body(
        "Credit committee is asked to approve a $7,200,000 allocation of the "
        "Apex Industrial Holdings first-lien term loan into the Northbridge CLO 2024-1 "
        "warehouse, and to roll that position into the CLO at closing. The loan is "
        "a $400,000,000 first-lien senior secured term loan due 2031. The borrower "
        "is Apex Industrial Holdings, a Delaware corporation headquartered in Chicago. "
        "The financial sponsor is Lakeside Private Equity. The facility agent is "
        "Summit National Bank. Analyst: Marcus Chen. Committee chair: David Okonkwo. "
        "Portfolio manager: Priya Raman, Meridian Credit Partners LLC."
    )
    pdf.body(
        "Recommendation: Approve at a maximum par of $7,200,000 (1.80% of the "
        "$400,000,000 target CLO portfolio). The name sits inside the 2.0% single "
        "obligor concentration limit in the Northbridge CLO 2024-1 indenture. "
        "Moody's corporate family rating is B1. S&P issuer credit rating is B+. "
        "The loan is first-lien, covenant-lite, and US dollar denominated, and is "
        "eligible collateral under the term sheet dated 12 March 2024."
    )
    pdf.heading("2. Borrower and sponsor")
    pdf.body(
        "Apex Industrial Holdings manufactures precision metal components for "
        "heavy equipment and aftermarket industrial parts. Approximately 70% of "
        "revenue is North America and 30% is Europe. The company is owned by "
        "Lakeside Private Equity, which completed a take-private in September 2022. "
        "Lakeside Private Equity is based in Chicago. The CEO is Elena Vasquez. "
        "The CFO is Thomas Berger. Neither person is employed by Meridian Credit "
        "Partners LLC."
    )
    pdf.body(
        "Key customers include Redwood Packaging LLC (also a seed name in "
        "Northbridge CLO 2024-1) and two original-equipment manufacturers that are "
        "not held in the CLO. Supplier concentration is moderate. The business is "
        "cyclical with construction and freight volumes."
    )
    pdf.heading("3. Facility terms")
    pdf.body(
        "Instrument: Apex Industrial Holdings first-lien term loan. Original "
        "principal $400,000,000. Spread: SOFR + 3.75% with a 0.75% floor. "
        "Maturity: 15 September 2031. Call protection: 101 soft call for six months. "
        "The credit agreement is covenant-lite; there is no springing leverage "
        "covenant on the term loan. A $75,000,000 revolving credit facility sits "
        "ahead of the term loan for liquidity only and is provided by Summit "
        "National Bank and Bridgeport Bank. Bridgeport Bank is also the warehouse "
        "lender to Northbridge CLO 2024-1."
    )
    pdf.add_page()
    pdf.heading("4. Credit highlights and risks")
    pdf.body(
        "Highlights: diversified end markets, sponsor support from Lakeside Private "
        "Equity, first-lien collateral package, and a loan-to-value that we estimate "
        "in the mid-50s on a last-twelve-months EBITDA of $148 million. Free cash "
        "flow after capex was $41 million in 2023. Interest coverage on the first-lien "
        "package is about 3.1x."
    )
    pdf.body(
        "Risks: cyclical industrial demand, customer concentration with Redwood "
        "Packaging LLC, and add-on acquisition risk. Helios Telecom, Inc. is not "
        "related to this borrower; it is a separate seed name in Northbridge CLO 2024-1 "
        "and should not be aggregated with Apex Industrial Holdings for the single "
        "obligor test. Marcus Chen confirmed that Moody's industry classification "
        "for Apex Industrial Holdings is 'Capital Equipment' and for Helios Telecom, "
        "Inc. is 'Telecommunications'."
    )
    pdf.heading("5. CLO fit and covenants")
    pdf.body(
        "The allocation complies with the Class A/B Overcollateralization Test "
        "methodology because the loan is par-eligible and rated above Caa1. It does "
        "not increase the Caa bucket. It uses 1.80 of the 2.00 percentage-point "
        "largest-obligor covenant. Priya Raman confirmed that after this trade, "
        "the next largest expected seed names are Helios Telecom, Inc. at 1.5% and "
        "Redwood Packaging LLC at 1.4%. Cascade Health Services is expected at 1.1%."
    )
    pdf.body(
        "If Apex Industrial Holdings is downgraded to Caa1, the position would "
        "count toward the 7.5% Caa bucket in the Northbridge CLO 2024-1 indenture. "
        "Harbor Trust Company, N.A. would reflect that classification on the next "
        "monthly trustee report. Meridian Credit Partners LLC would then evaluate "
        "a sale during the reinvestment period."
    )
    pdf.heading("6. Committee decision")
    pdf.body(
        "Credit committee of Meridian Credit Partners LLC approved the $7,200,000 "
        "purchase for the Northbridge CLO 2024-1 warehouse on 4 March 2024. "
        "Voting members: David Okonkwo (chair), Priya Raman, and Marcus Chen. "
        "The trade will settle into the Bridgeport Bank warehouse and be conveyed "
        "to Northbridge CLO 2024-1, Ltd. on the closing date of 28 March 2024."
    )
    return _write(pdf, "northbridge-clo-2024-1-apex-credit-memo.pdf")


def build_monthly_report() -> Path:
    pdf = CloPdf(
        "Monthly Trustee Report",
        "Northbridge CLO 2024-1  |  Report date 31 August 2024  |  Determination 15 August 2024",
    )
    pdf.add_page()
    pdf.heading("1. Report identification")
    pdf.body(
        "Harbor Trust Company, N.A., as Trustee and collateral administrator for "
        "Northbridge CLO 2024-1, Ltd. and Northbridge CLO 2024-1, LLC, delivers "
        "this monthly report to noteholders. Collateral Manager: Meridian Credit "
        "Partners LLC. Portfolio manager: Priya Raman. Payment date: 20 September 2024. "
        "This report is a fictional sample for software testing and does not describe "
        "a live securitization."
    )
    pdf.heading("2. Capital structure outstanding")
    pdf.body(
        "Outstanding note balances as of the determination date are unchanged from "
        "closing except for a $1,200,000 paydown on the Class A Senior Secured "
        "Floating Rate Notes from unscheduled principal. Subordinated Notes remain "
        "$32,000,000. Class B, Class C, Class D, and Class E notes remain at original "
        "par. The Trustee confirms that interest was paid in full on all rated notes "
        "on the August payment date."
    )
    pdf.heading("3. Coverage test results")
    pdf.body(
        "All coverage tests passed on the determination date. Harbor Trust Company, "
        "N.A. calculated the ratios below using the indenture definitions. No "
        "redirection of interest proceeds is required this period."
    )
    pdf.bullet("Class A/B Overcollateralization Test: 124.1% vs 122.5% trigger. Pass.")
    pdf.bullet("Class A/B Interest Coverage Test: 131.6% vs 120.0% trigger. Pass.")
    pdf.bullet("Class C Overcollateralization Test: 116.2% vs 114.0% trigger. Pass.")
    pdf.bullet("Class D Overcollateralization Test: 110.0% vs 108.5% trigger. Pass.")
    pdf.bullet("Interest Diversion Test (Class E par coverage): 105.8% vs 104.5%. Pass.")
    pdf.heading("4. Largest obligors")
    pdf.body(
        "The five largest obligors as a percentage of collateral principal amount "
        "are listed below. The largest-obligor concentration limit remains 2.0%."
    )
    pdf.bullet(
        "Apex Industrial Holdings: 1.82%. First-lien term loan. Sponsor: Lakeside "
        "Private Equity. Rating B1/B+. Chicago. No watch. This name was approved "
        "in the 4 March 2024 credit memorandum prepared by Marcus Chen."
    )
    pdf.bullet(
        "Helios Telecom, Inc.: 1.61%. First-lien term loan. Sponsor: Orion Capital "
        "Partners. Rating B2/B. Dallas. The Collateral Manager placed Helios Telecom, "
        "Inc. on internal watch on 12 August 2024 after a missed internal EBITDA "
        "covenant on the revolving facility at the issuer. The CLO loan itself is "
        "covenant-lite and is not in default."
    )
    pdf.bullet(
        "Redwood Packaging LLC: 1.44%. First-lien term loan. Customer overlap with "
        "Apex Industrial Holdings is noted but the names are separate obligors."
    )
    pdf.bullet("Cascade Health Services: 1.18%. Unitranche. Boston.")
    pdf.bullet("Summit Logistics Corp.: 1.05%. First-lien term loan. Atlanta.")
    pdf.add_page()
    pdf.heading("5. Watchlist and trading")
    pdf.body(
        "Priya Raman of Meridian Credit Partners LLC advised the Trustee that "
        "Helios Telecom, Inc. is the only credit on the official watchlist. "
        "David Okonkwo, chief credit officer, authorized a $2,000,000 par sale of "
        "Helios Telecom, Inc. during the reinvestment period if the bid is at or "
        "above 97.00. No sale settled in this period. Apex Industrial Holdings "
        "is not on watch. Redwood Packaging LLC remains performing."
    )
    pdf.body(
        "Reinvestment: Meridian Credit Partners LLC purchased $3,500,000 par of "
        "Summit Logistics Corp. first-lien term loan on 8 August 2024. The loan "
        "is eligible collateral, US dollar first-lien, and rated B1. The trade "
        "complies with the Class A/B Overcollateralization Test and the 2.0% "
        "obligor limit. Harbor Trust Company, N.A. settled the purchase into "
        "the custodial account in New York."
    )
    pdf.heading("6. Concentration and Caa bucket")
    pdf.body(
        "Caa bucket (Moody's Caa1 or below): 3.2% versus a 7.5% limit. No second-lien "
        "exposure. Covenant-lite share: 84%. Non-US obligors: 6.4%, all in Canada. "
        "Largest Moody's industry is Capital Equipment at 9.8%, which includes "
        "Apex Industrial Holdings and is below the 12.0% industry limit. "
        "Telecommunications, including Helios Telecom, Inc., is 4.1%."
    )
    pdf.heading("7. Notices")
    pdf.body(
        "Noteholders with questions should contact Harbor Trust Company, N.A. "
        "in Wilmington, or the Collateral Manager, Meridian Credit Partners LLC, "
        "in New York. Northbridge CLO 2024-1 remains in its reinvestment period "
        "until 28 March 2029. This report should be read with the 12 March 2024 "
        "term sheet and the Apex Industrial Holdings credit memorandum dated "
        "4 March 2024."
    )
    return _write(pdf, "northbridge-clo-2024-1-monthly-report-aug-2024.pdf")


def main() -> None:
    paths = [build_term_sheet(), build_credit_memo(), build_monthly_report()]
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
