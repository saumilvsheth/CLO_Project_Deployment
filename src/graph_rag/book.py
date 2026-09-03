"""Northbridge CLO 2024-1 book: obligors, unused commitments, and note waterfalls."""

from __future__ import annotations

from copy import deepcopy

DEAL = {
    "name": "Northbridge CLO 2024-1",
    "manager": "Meridian Credit Partners LLC",
    "trustee": "Harbor Trust Company, N.A.",
    "portfolioPar": 400_000_000,
    "fundingPool": 5_000_000,
}

# Unused delayed-draw / revolver room the desk can still fund.
OBLIGORS = [
    {
        "id": "apex",
        "name": "Apex Industrial Holdings",
        "sponsor": "Lakeside Private Equity",
        "location": "Chicago",
        "heldPar": 7_200_000,
        "unusedCommitment": 1_800_000,
        "rate": "SOFR + 3.75%",
        "watch": False,
    },
    {
        "id": "helios",
        "name": "Helios Telecom, Inc.",
        "sponsor": "Orion Capital Partners",
        "location": "Dallas",
        "heldPar": 6_440_000,
        "unusedCommitment": 1_200_000,
        "rate": "SOFR + 4.25%",
        "watch": True,
    },
    {
        "id": "redwood",
        "name": "Redwood Packaging LLC",
        "sponsor": "Independent",
        "location": "United States",
        "heldPar": 5_760_000,
        "unusedCommitment": 900_000,
        "rate": "SOFR + 3.50%",
        "watch": False,
    },
    {
        "id": "cascade",
        "name": "Cascade Health Services",
        "sponsor": "Independent",
        "location": "Boston",
        "heldPar": 4_720_000,
        "unusedCommitment": 700_000,
        "rate": "SOFR + 3.25%",
        "watch": False,
    },
    {
        "id": "summit",
        "name": "Summit Logistics Corp.",
        "sponsor": "Independent",
        "location": "Atlanta",
        "heldPar": 4_200_000,
        "unusedCommitment": 400_000,
        "rate": "SOFR + 3.60%",
        "watch": False,
    },
]

TRANCHES = [
    {"id": "a", "name": "Class A", "balance": 246_800_000, "spread": "SOFR + 1.45%"},
    {"id": "b", "name": "Class B", "balance": 36_000_000, "spread": "SOFR + 2.10%"},
    {"id": "c", "name": "Class C", "balance": 24_000_000, "spread": "SOFR + 2.85%"},
    {"id": "d", "name": "Class D", "balance": 18_000_000, "spread": "SOFR + 4.20%"},
    {"id": "e", "name": "Class E", "balance": 14_000_000, "spread": "SOFR + 7.15%"},
    {"id": "sub", "name": "Subordinated notes", "balance": 32_000_000, "spread": "Residual"},
]


def seed_obligors() -> list[dict]:
    return deepcopy(OBLIGORS)


def waterfall(amount: float) -> list[dict]:
    """Pay collected cash down the note stack, senior first."""
    remaining = max(0.0, float(amount))
    rows = []
    for tranche in TRANCHES:
        pay = min(remaining, float(tranche["balance"]))
        remaining -= pay
        rows.append(
            {
                "id": tranche["id"],
                "name": tranche["name"],
                "balance": tranche["balance"],
                "spread": tranche["spread"],
                "paid": round(pay, 2),
            }
        )
    return rows
