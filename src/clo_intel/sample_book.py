"""Fictional CLO sample book. PDFs, extraction fields, and titles all read from here."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Obligor:
    name: str
    slug: str
    sponsor: str
    moodys: str
    sp: str
    allocation: str
    pct: str
    city: str
    industry: str
    instrument: str = "first-lien term loan"
    watch: bool = False

    @property
    def short_name(self) -> str:
        return (
            self.name.replace(", Inc.", "")
            .replace(" Inc.", "")
            .replace(", LLC", "")
            .replace(" LLC", "")
            .replace(" Corp.", "")
            .replace(" Holdings", "")
            .strip()
        )


@dataclass(frozen=True)
class Deal:
    id: str
    series: str
    year: int
    manager: str
    manager_parent: str
    manager_city: str
    trustee: str
    trustee_city: str
    pm: str
    cco: str
    analyst: str
    class_a_par: str
    class_b_par: str
    class_c_par: str
    class_d_par: str
    class_e_par: str
    sub_par: str
    oc_ab_trigger: str
    oc_ab_result: str
    oc_ab_pass: bool
    ic_ab_trigger: str
    ic_ab_result: str
    ic_ab_pass: bool
    oc_c_trigger: str
    oc_c_result: str
    oc_d_trigger: str
    oc_d_result: str
    diversion_trigger: str
    diversion_result: str
    caa_pct: str
    warehouse: str
    placement: str
    counsel: str
    target_par: str
    close: str
    term_sheet_date: str
    memo_date: str
    report_date: str
    report_month: str
    report_slug: str
    determination: str
    payment_date: str
    reinvestment_end: str
    obligors: tuple[Obligor, ...]

    @property
    def issuer(self) -> str:
        return f"{self.series}, Ltd."

    @property
    def co_issuer(self) -> str:
        return f"{self.series}, LLC"

    @property
    def primary(self) -> Obligor:
        return self.obligors[0]

    def term_sheet_id(self) -> str:
        return f"{self.id}-term-sheet"

    def credit_memo_id(self) -> str:
        return f"{self.id}-{self.primary.slug}-credit-memo"

    def report_id(self) -> str:
        return f"{self.id}-monthly-report-{self.report_slug}"


def _money(amount: int) -> str:
    return f"${amount:,}"


def _obl(
    name: str,
    slug: str,
    sponsor: str,
    moodys: str,
    sp: str,
    allocation: int,
    pct: str,
    city: str,
    industry: str,
    instrument: str = "first-lien term loan",
    watch: bool = False,
) -> Obligor:
    return Obligor(
        name=name,
        slug=slug,
        sponsor=sponsor,
        moodys=moodys,
        sp=sp,
        allocation=_money(allocation),
        pct=pct,
        city=city,
        industry=industry,
        instrument=instrument,
        watch=watch,
    )


def apex(**kw) -> Obligor:
    defaults = dict(
        name="Apex Industrial Holdings",
        slug="apex",
        sponsor="Lakeside Private Equity",
        moodys="B1",
        sp="B+",
        allocation=7_200_000,
        pct="1.82",
        city="Chicago",
        industry="Capital Equipment",
    )
    defaults.update(kw)
    return _obl(**defaults)


def helios(**kw) -> Obligor:
    defaults = dict(
        name="Helios Telecom, Inc.",
        slug="helios",
        sponsor="Orion Capital Partners",
        moodys="B2",
        sp="B",
        allocation=6_400_000,
        pct="1.61",
        city="Dallas",
        industry="Telecommunications",
        watch=True,
    )
    defaults.update(kw)
    return _obl(**defaults)


def redwood(**kw) -> Obligor:
    defaults = dict(
        name="Redwood Packaging LLC",
        slug="redwood",
        sponsor="Pioneer Packaging Partners",
        moodys="B1",
        sp="B+",
        allocation=5_760_000,
        pct="1.44",
        city="Portland",
        industry="Containers",
    )
    defaults.update(kw)
    return _obl(**defaults)


def cascade(**kw) -> Obligor:
    defaults = dict(
        name="Cascade Health Services",
        slug="cascade",
        sponsor="Northline Healthcare",
        moodys="B2",
        sp="B",
        allocation=4_720_000,
        pct="1.18",
        city="Boston",
        industry="Healthcare",
        instrument="unitranche",
    )
    defaults.update(kw)
    return _obl(**defaults)


def summit(**kw) -> Obligor:
    defaults = dict(
        name="Summit Logistics Corp.",
        slug="summit",
        sponsor="Trailhead Equity",
        moodys="B1",
        sp="B+",
        allocation=4_200_000,
        pct="1.05",
        city="Atlanta",
        industry="Transportation",
    )
    defaults.update(kw)
    return _obl(**defaults)


_MANAGERS = {
    "meridian": (
        "Meridian Credit Partners LLC",
        "Meridian Holdings LP",
        "New York",
        "Priya Raman",
        "David Okonkwo",
        "Marcus Chen",
    ),
    "atlas": (
        "Atlas Loan Management LLC",
        "Atlas Credit Group LP",
        "Boston",
        "James Whitfield",
        "Helen Park",
        "Nina Okeke",
    ),
    "beacon": (
        "Beacon Hill Credit LLC",
        "Beacon Hill Holdings LLC",
        "Boston",
        "Amina Solace",
        "Robert Lang",
        "Diego Vargas",
    ),
    "crestview": (
        "Crestview CLO Advisors LLC",
        "Crestview Financial LP",
        "Chicago",
        "Wei Nakamura",
        "Claire Fontaine",
        "Samuel Ortiz",
    ),
    "dunhill": (
        "Dunhill Credit Partners LP",
        "Dunhill Capital Ltd",
        "Dallas",
        "Sofia Almeida",
        "Peter Groves",
        "Leah Brooks",
    ),
    "evergreen": (
        "Evergreen Loan Strategies LLC",
        "Evergreen Partners LP",
        "San Francisco",
        "Noah Patel",
        "Iris Benoit",
        "Kevin Zhou",
    ),
    "falcon": (
        "Falcon Tree Capital LLC",
        "Falcon Tree Holdings LP",
        "New York",
        "Maya Ellison",
        "Andre Copeland",
        "Ruth Kim",
    ),
    "granite": (
        "Granite Harbor Management LLC",
        "Granite Harbor LP",
        "Minneapolis",
        "Owen Briggs",
        "Fatima Rahman",
        "Chris Nolan",
    ),
}

_TRUSTEES = {
    "harbor": ("Harbor Trust Company, N.A.", "Wilmington"),
    "wilmington": ("Wilmington Trust, N.A.", "Wilmington"),
    "usbank": ("U.S. Bank Trust Company, N.A.", "St. Paul"),
    "citi": ("Citibank, N.A.", "New York"),
}


def _deal(
    *,
    id: str,
    series: str,
    year: int,
    manager: str,
    trustee: str,
    class_a: int,
    oc_trig: str,
    oc_res: str,
    oc_pass: bool = True,
    ic_trig: str = "120.0",
    ic_res: str = "131.6",
    ic_pass: bool = True,
    report_month: str | None = None,
    report_slug: str | None = None,
    warehouse: str = "Bridgeport Bank",
    placement: str = "Westfield Securities LLC",
    counsel: str = "Hale & Martin LLP",
    target_par: str = "$400,000,000",
    obligors: tuple[Obligor, ...],
    caa_pct: str = "3.2",
) -> Deal:
    mgr = _MANAGERS[manager]
    tr = _TRUSTEES[trustee]
    if year == 2023:
        month, slug, close, ts, memo, rep, det, pay, rei = (
            "November 2023",
            "nov-2023",
            "16 November 2023",
            "2 November 2023",
            "20 October 2023",
            "30 November 2023",
            "15 November 2023",
            "20 December 2023",
            "16 November 2028",
        )
    elif year == 2025:
        month, slug, close, ts, memo, rep, det, pay, rei = (
            "March 2025",
            "mar-2025",
            "20 March 2025",
            "6 March 2025",
            "24 February 2025",
            "31 March 2025",
            "15 March 2025",
            "18 April 2025",
            "20 March 2030",
        )
    else:
        month, slug, close, ts, memo, rep, det, pay, rei = (
            "August 2024",
            "aug-2024",
            "28 March 2024",
            "12 March 2024",
            "4 March 2024",
            "31 August 2024",
            "15 August 2024",
            "20 September 2024",
            "28 March 2029",
        )
    return Deal(
        id=id,
        series=series,
        year=year,
        manager=mgr[0],
        manager_parent=mgr[1],
        manager_city=mgr[2],
        trustee=tr[0],
        trustee_city=tr[1],
        pm=mgr[3],
        cco=mgr[4],
        analyst=mgr[5],
        class_a_par=_money(class_a),
        class_b_par=_money(int(class_a * 0.145)),
        class_c_par=_money(int(class_a * 0.097)),
        class_d_par=_money(int(class_a * 0.073)),
        class_e_par=_money(int(class_a * 0.056)),
        sub_par=_money(int(class_a * 0.129)),
        oc_ab_trigger=oc_trig,
        oc_ab_result=oc_res,
        oc_ab_pass=oc_pass,
        ic_ab_trigger=ic_trig,
        ic_ab_result=ic_res,
        ic_ab_pass=ic_pass,
        oc_c_trigger="114.0",
        oc_c_result="116.2" if oc_pass else "113.1",
        oc_d_trigger="108.5",
        oc_d_result="110.0" if oc_pass else "107.4",
        diversion_trigger="104.5",
        diversion_result="105.8" if oc_pass else "103.9",
        caa_pct=caa_pct,
        warehouse=warehouse,
        placement=placement,
        counsel=counsel,
        target_par=target_par,
        close=close,
        term_sheet_date=ts,
        memo_date=memo,
        report_date=rep,
        report_month=report_month or month,
        report_slug=report_slug or slug,
        determination=det,
        payment_date=pay,
        reinvestment_end=rei,
        obligors=obligors,
    )


# 22 fictional deals. Overlapping obligors (Apex, Helios, Redwood, Cascade, Summit)
# are intentional so a later graph can answer cross-deal questions.
DEALS: tuple[Deal, ...] = (
    _deal(
        id="northbridge-clo-2024-1",
        series="Northbridge CLO 2024-1",
        year=2024,
        manager="meridian",
        trustee="harbor",
        class_a=248_000_000,
        oc_trig="122.5",
        oc_res="124.1",
        report_month="August 2024",
        report_slug="aug-2024",
        obligors=(
            apex(),
            helios(),
            redwood(),
            cascade(),
            summit(),
        ),
    ),
    _deal(
        id="silverlake-clo-2024-2",
        series="Silverlake CLO 2024-2",
        year=2024,
        manager="atlas",
        trustee="wilmington",
        class_a=310_000_000,
        oc_trig="123.0",
        oc_res="125.4",
        warehouse="Lakeshore Funding",
        obligors=(
            redwood(allocation=8_400_000, pct="1.91"),
            _obl("Nimbus Software, Inc.", "nimbus", "Skyline Ventures", "B2", "B", 6_200_000, "1.41", "Austin", "Technology"),
            _obl("Harborlight Foods LLC", "harborlight", "Grainstone Capital", "B1", "B+", 5_100_000, "1.16", "Minneapolis", "Consumer"),
            summit(allocation=4_600_000, pct="1.05"),
            _obl("Velvet Rail Media", "velvet", "Orchard Media Partners", "B3", "B-", 3_900_000, "0.89", "Los Angeles", "Media"),
        ),
    ),
    _deal(
        id="harborview-clo-2023-3",
        series="Harborview CLO 2023-3",
        year=2023,
        manager="beacon",
        trustee="usbank",
        class_a=275_000_000,
        oc_trig="122.0",
        oc_res="123.8",
        warehouse="East Pier Bank",
        obligors=(
            _obl("Mariner Energy Holdings", "mariner", "Tidepool Energy", "Ba3", "BB-", 7_000_000, "1.75", "Houston", "Energy"),
            _obl("Quarry Lane Materials", "quarry", "Bedrock Partners", "B1", "B+", 5_800_000, "1.45", "Denver", "Building Materials"),
            _obl("Lumen Dental Groups", "lumen", "Whiteoak Healthcare", "B2", "B", 5_000_000, "1.25", "Nashville", "Healthcare"),
            _obl("Parcel North Logistics", "parcel", "Trailhead Equity", "B1", "B+", 4_400_000, "1.10", "Chicago", "Transportation"),
            _obl("Ironclad Security, Inc.", "ironclad", "Watchtower Equity", "B3", "B-", 3_600_000, "0.90", "Phoenix", "Services", watch=True),
        ),
    ),
    _deal(
        id="ironwood-clo-2024-1",
        series="Ironwood CLO 2024-1",
        year=2024,
        manager="crestview",
        trustee="citi",
        class_a=265_000_000,
        oc_trig="122.5",
        oc_res="123.9",
        warehouse="Summit National Bank",
        obligors=(
            apex(allocation=6_800_000, pct="1.70"),
            _obl("Boreal Timber Co.", "boreal", "Greenmast Capital", "B1", "B+", 5_500_000, "1.38", "Seattle", "Paper"),
            _obl("Keystone Auto Parts", "keystone", "Axle Partners", "B2", "B", 4_900_000, "1.23", "Detroit", "Automotive"),
            _obl("Sable Insurance Services", "sable", "Northline Healthcare", "B1", "B+", 4_200_000, "1.05", "Hartford", "Insurance"),
            helios(allocation=3_800_000, pct="0.95", watch=False),
        ),
    ),
    _deal(
        id="palisades-clo-2023-2",
        series="Palisades CLO 2023-2",
        year=2023,
        manager="dunhill",
        trustee="harbor",
        class_a=198_000_000,
        oc_trig="121.8",
        oc_res="123.1",
        warehouse="Hudson Warehouse Bank",
        obligors=(
            summit(allocation=6_100_000, pct="1.74"),
            _obl("Cinder Hotel Group", "cinder", "Lantern Hospitality", "B2", "B", 5_200_000, "1.49", "Orlando", "Lodging"),
            _obl("Arcadia Labs, Inc.", "arcadia", "Helix Venture Partners", "B3", "B-", 4_400_000, "1.26", "Cambridge", "Healthcare", watch=True),
            _obl("Foothill Utilities LLC", "foothill", "Prairie Infrastructure", "Ba3", "BB-", 3_900_000, "1.11", "Des Moines", "Utilities"),
            redwood(allocation=3_500_000, pct="1.00"),
        ),
    ),
    _deal(
        id="redrock-clo-2024-3",
        series="Redrock CLO 2024-3",
        year=2024,
        manager="evergreen",
        trustee="wilmington",
        class_a=288_000_000,
        oc_trig="122.5",
        oc_res="121.2",
        oc_pass=False,
        caa_pct="6.8",
        warehouse="Canyon Bridge Bank",
        obligors=(
            _obl("Dustline Mining Corp.", "dustline", "Red Mesa Capital", "Caa1", "CCC+", 7_400_000, "1.85", "Tucson", "Metals", watch=True),
            _obl("Sonora Retail Partners", "sonora", "Desert Palm Equity", "B3", "B-", 6_100_000, "1.53", "Phoenix", "Retail"),
            _obl("Mesa Wireless, Inc.", "mesa", "Orion Capital Partners", "B2", "B", 5_000_000, "1.25", "Albuquerque", "Telecommunications"),
            apex(allocation=4_400_000, pct="1.10"),
            _obl("Copperstate Construction", "copperstate", "Bedrock Partners", "B1", "B+", 3_800_000, "0.95", "Phoenix", "Building Materials"),
        ),
    ),
    _deal(
        id="windward-clo-2025-1",
        series="Windward CLO 2025-1",
        year=2025,
        manager="falcon",
        trustee="usbank",
        class_a=330_000_000,
        oc_trig="123.5",
        oc_res="125.0",
        warehouse="Atlantic Wharf Bank",
        obligors=(
            helios(allocation=7_800_000, pct="1.77"),
            _obl("North Cape Fisheries", "northcape", "Tidepool Energy", "B1", "B+", 6_000_000, "1.36", "Portland", "Consumer"),
            _obl("Gale Force Aviation", "gale", "Skyline Ventures", "B2", "B", 5_400_000, "1.23", "Seattle", "Transportation"),
            _obl("Lantern Bio, Inc.", "lantern", "Helix Venture Partners", "B3", "B-", 4_700_000, "1.07", "San Diego", "Healthcare"),
            cascade(allocation=4_100_000, pct="0.93"),
        ),
    ),
    _deal(
        id="stonehaven-clo-2024-1",
        series="Stonehaven CLO 2024-1",
        year=2024,
        manager="granite",
        trustee="citi",
        class_a=220_000_000,
        oc_trig="122.0",
        oc_res="124.6",
        warehouse="Twin Cities Warehouse",
        obligors=(
            _obl("Granite Peak Resorts", "granitepeak", "Alpine Leisure Partners", "B1", "B+", 6_600_000, "1.65", "Denver", "Lodging"),
            _obl("Prairie Grain Co.", "prairie", "Grainstone Capital", "Ba3", "BB-", 5_400_000, "1.35", "Omaha", "Consumer"),
            _obl("Midcontinent Rail LLC", "midcon", "Trailhead Equity", "B1", "B+", 4_800_000, "1.20", "Kansas City", "Transportation"),
            _obl("Clearwater Diagnostics", "clearwater", "Whiteoak Healthcare", "B2", "B", 4_000_000, "1.00", "Madison", "Healthcare"),
            _obl("Northwoods Paper Mills", "northwoods", "Greenmast Capital", "B2", "B", 3_400_000, "0.85", "Duluth", "Paper"),
        ),
    ),
    _deal(
        id="bluewater-clo-2023-1",
        series="Bluewater CLO 2023-1",
        year=2023,
        manager="meridian",
        trustee="harbor",
        class_a=240_000_000,
        oc_trig="122.5",
        oc_res="123.3",
        warehouse="Bridgeport Bank",
        obligors=(
            cascade(allocation=7_000_000, pct="1.75"),
            _obl("Atlantic Cage-Free Farms", "atlantic", "Grainstone Capital", "B1", "B+", 5_600_000, "1.40", "Richmond", "Consumer"),
            _obl("Seaboard Telecom LLC", "seaboard", "Orion Capital Partners", "B2", "B", 5_000_000, "1.25", "Norfolk", "Telecommunications"),
            _obl("Harbor Crane Works", "crane", "Bedrock Partners", "B1", "B+", 4_300_000, "1.08", "Baltimore", "Capital Equipment"),
            helios(allocation=3_700_000, pct="0.93", watch=False),
        ),
    ),
    _deal(
        id="cedar-ridge-clo-2024-2",
        series="Cedar Ridge CLO 2024-2",
        year=2024,
        manager="atlas",
        trustee="wilmington",
        class_a=305_000_000,
        oc_trig="123.0",
        oc_res="124.8",
        warehouse="Lakeshore Funding",
        obligors=(
            _obl("Cedarline Furniture", "cedarline", "Pioneer Packaging Partners", "B1", "B+", 7_100_000, "1.62", "Grand Rapids", "Consumer"),
            _obl("Ridgeway Pharma LLC", "ridgeway", "Helix Venture Partners", "B2", "B", 6_000_000, "1.37", "Indianapolis", "Healthcare"),
            redwood(allocation=5_200_000, pct="1.19"),
            _obl("Lakeshore Credit Union Processor", "lakeshore", "Watchtower Equity", "Ba3", "BB-", 4_500_000, "1.03", "Milwaukee", "Services"),
            _obl("Hearthstone Home Centers", "hearthstone", "Desert Palm Equity", "B3", "B-", 3_800_000, "0.87", "Cincinnati", "Retail"),
        ),
    ),
    _deal(
        id="fairmont-clo-2025-1",
        series="Fairmont CLO 2025-1",
        year=2025,
        manager="beacon",
        trustee="usbank",
        class_a=355_000_000,
        oc_trig="124.0",
        oc_res="125.7",
        warehouse="East Pier Bank",
        obligors=(
            apex(allocation=8_100_000, pct="1.80"),
            _obl("Fairmont Circuit, Inc.", "fairmontc", "Skyline Ventures", "B2", "B", 6_400_000, "1.42", "San Jose", "Technology"),
            _obl("Beacon Orthopedics", "beaconortho", "Whiteoak Healthcare", "B1", "B+", 5_500_000, "1.22", "Boston", "Healthcare"),
            summit(allocation=4_800_000, pct="1.07"),
            _obl("Commonwealth Power Services", "commonwealth", "Prairie Infrastructure", "Ba3", "BB-", 4_000_000, "0.89", "Hartford", "Utilities"),
        ),
    ),
    _deal(
        id="kingswood-clo-2024-1",
        series="Kingswood CLO 2024-1",
        year=2024,
        manager="crestview",
        trustee="citi",
        class_a=215_000_000,
        oc_trig="122.0",
        oc_res="123.6",
        warehouse="Summit National Bank",
        obligors=(
            _obl("Kingswood Academies", "kingswood", "Lantern Hospitality", "B2", "B", 6_300_000, "1.58", "Philadelphia", "Services"),
            _obl("Liberty Bridge Steel", "liberty", "Bedrock Partners", "B1", "B+", 5_400_000, "1.35", "Pittsburgh", "Metals"),
            _obl("Schuylkill Water Co.", "schuylkill", "Prairie Infrastructure", "Ba3", "BB-", 4_600_000, "1.15", "Philadelphia", "Utilities"),
            _obl("Penn Valley Foods", "pennvalley", "Grainstone Capital", "B1", "B+", 4_000_000, "1.00", "Lancaster", "Consumer"),
            _obl("Independence Labs", "independence", "Helix Venture Partners", "B3", "B-", 3_300_000, "0.83", "Philadelphia", "Healthcare"),
        ),
    ),
    _deal(
        id="maplewood-clo-2023-4",
        series="Maplewood CLO 2023-4",
        year=2023,
        manager="dunhill",
        trustee="harbor",
        class_a=260_000_000,
        oc_trig="122.5",
        oc_res="123.0",
        ic_trig="120.0",
        ic_res="118.4",
        ic_pass=False,
        warehouse="Hudson Warehouse Bank",
        obligors=(
            _obl("Maplewood Paperboard", "maplewood", "Greenmast Capital", "B2", "B", 6_900_000, "1.73", "Green Bay", "Paper"),
            _obl("Fox River Plastics", "foxriver", "Pioneer Packaging Partners", "B1", "B+", 5_700_000, "1.43", "Appleton", "Containers"),
            cascade(allocation=5_000_000, pct="1.25"),
            _obl("Badger Medical Devices", "badger", "Whiteoak Healthcare", "B2", "B", 4_200_000, "1.05", "Madison", "Healthcare", watch=True),
            _obl("Lakefront Cold Storage", "lakefront", "Trailhead Equity", "B1", "B+", 3_600_000, "0.90", "Milwaukee", "Transportation"),
        ),
    ),
    _deal(
        id="oakmont-clo-2024-2",
        series="Oakmont CLO 2024-2",
        year=2024,
        manager="evergreen",
        trustee="wilmington",
        class_a=292_000_000,
        oc_trig="123.0",
        oc_res="121.4",
        oc_pass=False,
        caa_pct="5.9",
        warehouse="Canyon Bridge Bank",
        obligors=(
            _obl("Oakmont Drilling LLC", "oakmont", "Tidepool Energy", "Caa1", "CCC+", 7_200_000, "1.80", "Oklahoma City", "Energy", watch=True),
            _obl("Redbud Convenience Stores", "redbud", "Desert Palm Equity", "B3", "B-", 5_900_000, "1.48", "Tulsa", "Retail"),
            _obl("Cimarron Wind Holdings", "cimarron", "Prairie Infrastructure", "B1", "B+", 5_100_000, "1.28", "Amarillo", "Utilities"),
            redwood(allocation=4_400_000, pct="1.10"),
            _obl("Sooner Staffing, Inc.", "sooner", "Watchtower Equity", "B2", "B", 3_700_000, "0.93", "Oklahoma City", "Services"),
        ),
    ),
    _deal(
        id="pinecrest-clo-2025-1",
        series="Pinecrest CLO 2025-1",
        year=2025,
        manager="falcon",
        trustee="usbank",
        class_a=340_000_000,
        oc_trig="123.5",
        oc_res="124.9",
        warehouse="Atlantic Wharf Bank",
        obligors=(
            helios(allocation=8_000_000, pct="1.78"),
            _obl("Pinecrest Outdoor Co.", "pinecrest", "Alpine Leisure Partners", "B1", "B+", 6_200_000, "1.38", "Boulder", "Consumer"),
            _obl("Summit County Broadband", "summitbb", "Orion Capital Partners", "B2", "B", 5_300_000, "1.18", "Denver", "Telecommunications"),
            apex(allocation=4_700_000, pct="1.04"),
            _obl("Front Range Clinics", "frontrange", "Northline Healthcare", "B2", "B", 4_000_000, "0.89", "Colorado Springs", "Healthcare"),
        ),
    ),
    _deal(
        id="riverton-clo-2024-1",
        series="Riverton CLO 2024-1",
        year=2024,
        manager="granite",
        trustee="citi",
        class_a=205_000_000,
        oc_trig="121.5",
        oc_res="123.2",
        warehouse="Twin Cities Warehouse",
        obligors=(
            _obl("Riverton Barge Lines", "riverton", "Trailhead Equity", "B1", "B+", 6_000_000, "1.50", "St. Louis", "Transportation"),
            _obl("Gateway Steel Fabricators", "gateway", "Bedrock Partners", "B2", "B", 5_100_000, "1.28", "St. Louis", "Metals"),
            _obl("Ozark Health Network", "ozark", "Whiteoak Healthcare", "B1", "B+", 4_500_000, "1.13", "Springfield", "Healthcare"),
            _obl("Mississippi Lime Co.", "mslime", "Red Mesa Capital", "Ba3", "BB-", 3_900_000, "0.98", "Cape Girardeau", "Building Materials"),
            _obl("Arch City Catering", "archcity", "Grainstone Capital", "B3", "B-", 3_200_000, "0.80", "St. Louis", "Consumer"),
        ),
    ),
    _deal(
        id="southport-clo-2023-2",
        series="Southport CLO 2023-2",
        year=2023,
        manager="meridian",
        trustee="harbor",
        class_a=228_000_000,
        oc_trig="122.5",
        oc_res="124.0",
        warehouse="Bridgeport Bank",
        obligors=(
            _obl("Southport Shipyard LLC", "southport", "Tidepool Energy", "B1", "B+", 6_500_000, "1.63", "Mobile", "Capital Equipment"),
            _obl("Gulf Breeze Hotels", "gulfbreeze", "Lantern Hospitality", "B2", "B", 5_400_000, "1.35", "Pensacola", "Lodging"),
            _obl("Bayou Chemical, Inc.", "bayou", "Red Mesa Capital", "B3", "B-", 4_800_000, "1.20", "Baton Rouge", "Chemicals", watch=True),
            cascade(allocation=4_100_000, pct="1.03"),
            _obl("Delta Cotton Holdings", "delta", "Grainstone Capital", "B1", "B+", 3_500_000, "0.88", "Memphis", "Consumer"),
        ),
    ),
    _deal(
        id="westbrook-clo-2024-3",
        series="Westbrook CLO 2024-3",
        year=2024,
        manager="atlas",
        trustee="wilmington",
        class_a=318_000_000,
        oc_trig="123.0",
        oc_res="125.1",
        warehouse="Lakeshore Funding",
        obligors=(
            redwood(allocation=8_800_000, pct="1.88"),
            _obl("Westbrook Data Centers", "westbrook", "Skyline Ventures", "B1", "B+", 6_600_000, "1.41", "Portland", "Technology"),
            _obl("Cascadia Berry Farms", "cascadia", "Grainstone Capital", "B2", "B", 5_200_000, "1.11", "Salem", "Consumer"),
            summit(allocation=4_700_000, pct="1.00"),
            _obl("Rainier Dental Partners", "rainier", "Northline Healthcare", "B1", "B+", 4_000_000, "0.85", "Tacoma", "Healthcare"),
        ),
    ),
    _deal(
        id="ashland-clo-2025-1",
        series="Ashland CLO 2025-1",
        year=2025,
        manager="beacon",
        trustee="usbank",
        class_a=270_000_000,
        oc_trig="122.8",
        oc_res="121.0",
        oc_pass=False,
        caa_pct="7.1",
        warehouse="East Pier Bank",
        obligors=(
            _obl("Ashland Fiber Mills", "ashland", "Greenmast Capital", "Caa1", "CCC+", 7_000_000, "1.75", "Richmond", "Paper", watch=True),
            _obl("James River Chemicals", "jamesriver", "Red Mesa Capital", "B3", "B-", 5_800_000, "1.45", "Richmond", "Chemicals"),
            _obl("Piedmont Auto Glass", "piedmont", "Axle Partners", "B2", "B", 4_900_000, "1.23", "Charlotte", "Automotive"),
            helios(allocation=4_200_000, pct="1.05"),
            _obl("Capital Beltway Storage", "beltway", "Trailhead Equity", "B1", "B+", 3_600_000, "0.90", "Arlington", "Transportation"),
        ),
    ),
    _deal(
        id="broadleaf-clo-2024-1",
        series="Broadleaf CLO 2024-1",
        year=2024,
        manager="crestview",
        trustee="citi",
        class_a=250_000_000,
        oc_trig="122.5",
        oc_res="123.7",
        warehouse="Summit National Bank",
        obligors=(
            summit(allocation=7_000_000, pct="1.75"),
            _obl("Broadleaf Canopy, Inc.", "broadleaf", "Greenmast Capital", "B1", "B+", 5_600_000, "1.40", "Portland", "Paper"),
            _obl("Willamette Clinics", "willamette", "Whiteoak Healthcare", "B2", "B", 4_800_000, "1.20", "Eugene", "Healthcare"),
            _obl("Oregon Trail Freight", "otfreight", "Trailhead Equity", "B1", "B+", 4_200_000, "1.05", "Boise", "Transportation"),
            _obl("Crater Lake Resorts", "crater", "Alpine Leisure Partners", "B2", "B", 3_500_000, "0.88", "Bend", "Lodging"),
        ),
    ),
    _deal(
        id="millfield-clo-2024-2",
        series="Millfield CLO 2024-2",
        year=2024,
        manager="dunhill",
        trustee="harbor",
        class_a=236_000_000,
        oc_trig="122.0",
        oc_res="123.4",
        warehouse="Hudson Warehouse Bank",
        obligors=(
            _obl("Millfield Yarns LLC", "millfield", "Pioneer Packaging Partners", "B1", "B+", 6_400_000, "1.60", "Charlotte", "Consumer"),
            _obl("Piedmont Power Co.", "piedmontpwr", "Prairie Infrastructure", "Ba3", "BB-", 5_300_000, "1.33", "Raleigh", "Utilities"),
            _obl("Carolina Petcare, Inc.", "carolinapet", "Skyline Ventures", "B2", "B", 4_600_000, "1.15", "Greensboro", "Consumer"),
            redwood(allocation=4_000_000, pct="1.00"),
            _obl("Outer Banks Inns", "outerbanks", "Lantern Hospitality", "B3", "B-", 3_400_000, "0.85", "Nags Head", "Lodging", watch=True),
        ),
    ),
    _deal(
        id="northstar-clo-2023-1",
        series="Northstar CLO 2023-1",
        year=2023,
        manager="falcon",
        trustee="usbank",
        class_a=284_000_000,
        oc_trig="122.5",
        oc_res="124.2",
        warehouse="Atlantic Wharf Bank",
        obligors=(
            _obl("Northstar Mining Services", "northstar", "Red Mesa Capital", "B2", "B", 6_800_000, "1.70", "Anchorage", "Metals"),
            _obl("Aurora Cold Chain", "aurora", "Trailhead Equity", "B1", "B+", 5_500_000, "1.38", "Anchorage", "Transportation"),
            _obl("Denali Health System", "denali", "Northline Healthcare", "B1", "B+", 4_900_000, "1.23", "Fairbanks", "Healthcare"),
            apex(allocation=4_300_000, pct="1.08"),
            _obl("Yukon Telecom Coop", "yukon", "Orion Capital Partners", "B3", "B-", 3_600_000, "0.90", "Juneau", "Telecommunications"),
        ),
    ),
)

_BY_ID = {deal.id: deal for deal in DEALS}

_LEGACY_FIELD_IDS = {
    ("northbridge-clo-2024-1-term-sheet", "deal-name"): "deal-name",
    ("northbridge-clo-2024-1-term-sheet", "manager"): "manager",
    ("northbridge-clo-2024-1-term-sheet", "trustee"): "trustee",
    ("northbridge-clo-2024-1-term-sheet", "pm"): "pm",
    ("northbridge-clo-2024-1-term-sheet", "class-a-par"): "class-a-par",
    ("northbridge-clo-2024-1-term-sheet", "oc-trigger"): "oc-trigger",
    ("northbridge-clo-2024-1-apex-credit-memo", "obligor"): "apex-name",
    ("northbridge-clo-2024-1-apex-credit-memo", "allocation"): "apex-allocation",
    ("northbridge-clo-2024-1-apex-credit-memo", "sponsor"): "apex-sponsor",
    ("northbridge-clo-2024-1-apex-credit-memo", "rating"): "apex-rating",
    ("northbridge-clo-2024-1-monthly-report-aug-2024", "oc-result"): "oc-result",
    ("northbridge-clo-2024-1-monthly-report-aug-2024", "watch"): "helios-watch",
}


def deal_for_document(doc_id: str) -> Deal | None:
    matches = [deal for deal in DEALS if doc_id == deal.id or doc_id.startswith(deal.id + "-")]
    if not matches:
        return None
    return max(matches, key=lambda deal: len(deal.id))


def deal_id_for_document(doc_id: str) -> str:
    deal = deal_for_document(doc_id)
    return deal.id if deal else ""


def title_for_filename(filename: str) -> str:
    stem = Path(filename).stem
    deal = deal_for_document(stem)
    if not deal:
        return stem.replace("-", " ")
    if stem.endswith("-term-sheet"):
        return f"{deal.series} term sheet"
    if "credit-memo" in stem:
        return f"{deal.primary.short_name} credit memorandum ({deal.series})"
    if "monthly-report" in stem:
        return f"{deal.series} {deal.report_month} trustee report"
    return deal.series


def document_sort_key(filename: str) -> tuple:
    stem = Path(filename).stem
    deal = deal_for_document(stem)
    deal_idx = next((i for i, row in enumerate(DEALS) if deal and row.id == deal.id), 999)
    if stem.endswith("-term-sheet"):
        kind = 0
    elif "credit-memo" in stem:
        kind = 1
    else:
        kind = 2
    return (deal_idx, kind, filename)


def _field_id(document_id: str, short: str) -> str:
    return _LEGACY_FIELD_IDS.get((document_id, short), f"{document_id}--{short}")


def deal_field_ids(deal: Deal) -> dict[str, str]:
    term = deal.term_sheet_id()
    memo = deal.credit_memo_id()
    report = deal.report_id()
    return {
        "deal_name": _field_id(term, "deal-name"),
        "manager": _field_id(term, "manager"),
        "trustee": _field_id(term, "trustee"),
        "pm": _field_id(term, "pm"),
        "class_a_par": _field_id(term, "class-a-par"),
        "oc_trigger": _field_id(term, "oc-trigger"),
        "obligor": _field_id(memo, "obligor"),
        "allocation": _field_id(memo, "allocation"),
        "sponsor": _field_id(memo, "sponsor"),
        "rating": _field_id(memo, "rating"),
        "oc_result": _field_id(report, "oc-result"),
        "watch": _field_id(report, "watch"),
    }


def field_specs() -> list[dict]:
    specs: list[dict] = []
    for deal in DEALS:
        term = deal.term_sheet_id()
        memo = deal.credit_memo_id()
        report = deal.report_id()
        watch = next((item for item in deal.obligors if item.watch), None)
        specs.extend(
            [
                {
                    "id": _field_id(term, "deal-name"),
                    "label": "Deal name",
                    "group": "Parties",
                    "document_id": term,
                    "quote": deal.issuer,
                    "value": deal.issuer,
                },
                {
                    "id": _field_id(term, "manager"),
                    "label": "Collateral manager",
                    "group": "Parties",
                    "document_id": term,
                    "quote": deal.manager,
                    "value": deal.manager,
                },
                {
                    "id": _field_id(term, "trustee"),
                    "label": "Trustee",
                    "group": "Parties",
                    "document_id": term,
                    "quote": deal.trustee,
                    "value": deal.trustee,
                },
                {
                    "id": _field_id(term, "pm"),
                    "label": "Portfolio manager",
                    "group": "Parties",
                    "document_id": term,
                    "quote": deal.pm,
                    "value": deal.pm,
                },
                {
                    "id": _field_id(term, "class-a-par"),
                    "label": "Class A par",
                    "group": "Capital structure",
                    "document_id": term,
                    "quote": deal.class_a_par,
                    "value": deal.class_a_par,
                    "kind": "money",
                },
                {
                    "id": _field_id(term, "oc-trigger"),
                    "label": "Class A/B OC trigger",
                    "group": "Covenants",
                    "document_id": term,
                    "quote": f"{deal.oc_ab_trigger}%",
                    "value": f"{deal.oc_ab_trigger}%",
                    "kind": "oc_ratio",
                },
                {
                    "id": _field_id(memo, "obligor"),
                    "label": "Obligor",
                    "group": deal.primary.short_name,
                    "document_id": memo,
                    "quote": deal.primary.name,
                    "value": deal.primary.name,
                },
                {
                    "id": _field_id(memo, "allocation"),
                    "label": "CLO allocation",
                    "group": deal.primary.short_name,
                    "document_id": memo,
                    "quote": deal.primary.allocation,
                    "value": deal.primary.allocation,
                    "kind": "money",
                },
                {
                    "id": _field_id(memo, "sponsor"),
                    "label": "Sponsor",
                    "group": deal.primary.short_name,
                    "document_id": memo,
                    "quote": deal.primary.sponsor,
                    "value": deal.primary.sponsor,
                },
                {
                    "id": _field_id(memo, "rating"),
                    "label": "Moody's rating",
                    "group": deal.primary.short_name,
                    "document_id": memo,
                    "quote": f"Moody's corporate family rating is {deal.primary.moodys}",
                    "value": deal.primary.moodys,
                },
                {
                    "id": _field_id(report, "oc-result"),
                    "label": "Class A/B OC result",
                    "group": f"{deal.report_month} report",
                    "document_id": report,
                    "quote": f"{deal.oc_ab_result}%",
                    "value": f"{deal.oc_ab_result}%",
                    "kind": "oc_ratio",
                },
                {
                    "id": _field_id(report, "watch"),
                    "label": "Watchlist name",
                    "group": f"{deal.report_month} report",
                    "document_id": report,
                    "quote": watch.name if watch else "no names are on the official watchlist",
                    "value": watch.name if watch else "None",
                },
            ]
        )
    return specs
