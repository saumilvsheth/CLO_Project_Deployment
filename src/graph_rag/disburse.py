"""Allocate a funding pool across obligors and keep a simple ledger."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from graph_rag.book import DEAL, seed_obligors, waterfall

LEDGER_PATH = Path(__file__).resolve().parents[2] / "data" / "disbursements.json"
_lock = Lock()


def _state() -> dict:
    if LEDGER_PATH.exists():
        return json.loads(LEDGER_PATH.read_text())
    return {
        "fundingRemaining": DEAL["fundingPool"],
        "obligors": seed_obligors(),
        "batches": [],
    }


def _save(state: dict) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(state, indent=2))


def snapshot() -> dict:
    with _lock:
        state = _state()
    return {
        "deal": DEAL,
        "fundingRemaining": state["fundingRemaining"],
        "obligors": state["obligors"],
        "batches": list(reversed(state["batches"]))[:20],
    }


def prorata_amounts(pool: float) -> dict[str, float]:
    with _lock:
        obligors = _state()["obligors"]
    room = [row for row in obligors if row["unusedCommitment"] > 0]
    total_room = sum(row["unusedCommitment"] for row in room)
    if total_room <= 0 or pool <= 0:
        return {row["id"]: 0.0 for row in obligors}
    spend = min(pool, total_room)
    amounts: dict[str, float] = {row["id"]: 0.0 for row in obligors}
    for row in room:
        amounts[row["id"]] = round(spend * row["unusedCommitment"] / total_room, 2)
    # Fix rounding so the last name absorbs leftover cents.
    delta = round(spend - sum(amounts.values()), 2)
    if room and delta:
        amounts[room[-1]["id"]] = round(amounts[room[-1]["id"]] + delta, 2)
    return amounts


def preview(amounts: dict[str, float]) -> dict:
    with _lock:
        state = _state()
    cleaned = _validate(state, amounts)
    total = round(sum(cleaned.values()), 2)
    allocations = []
    for row in state["obligors"]:
        proposed = cleaned.get(row["id"], 0.0)
        allocations.append(
            {
                **row,
                "proposed": proposed,
                "unusedAfter": round(row["unusedCommitment"] - proposed, 2),
            }
        )
    return {
        "total": total,
        "fundingRemaining": state["fundingRemaining"],
        "fundingAfter": round(state["fundingRemaining"] - total, 2),
        "allocations": allocations,
        "noteholderWaterfall": waterfall(total),
    }


def commit(amounts: dict[str, float], memo: str) -> dict:
    with _lock:
        state = _state()
        cleaned = _validate(state, amounts)
        total = round(sum(cleaned.values()), 2)
        if total <= 0:
            raise ValueError("Enter at least one positive disbursement.")
        if total - state["fundingRemaining"] > 0.01:
            raise ValueError("Disbursement exceeds remaining funding pool.")
        for row in state["obligors"]:
            pay = cleaned.get(row["id"], 0.0)
            row["unusedCommitment"] = round(row["unusedCommitment"] - pay, 2)
            row["heldPar"] = round(row["heldPar"] + pay, 2)
        state["fundingRemaining"] = round(state["fundingRemaining"] - total, 2)
        batch = {
            "id": f"dsb-{len(state['batches']) + 1:04d}",
            "at": datetime.now(timezone.utc).isoformat(),
            "memo": memo.strip() or "Obligor advance",
            "total": total,
            "lines": [
                {"id": oid, "amount": amt} for oid, amt in cleaned.items() if amt > 0
            ],
        }
        state["batches"].append(batch)
        _save(state)
    return {"batch": batch, "book": snapshot()}


def _validate(state: dict, amounts: dict[str, float]) -> dict[str, float]:
    known = {row["id"]: row for row in state["obligors"]}
    cleaned: dict[str, float] = {}
    for oid, raw in amounts.items():
        if oid not in known:
            raise ValueError(f"Unknown obligor: {oid}")
        amount = round(float(raw or 0), 2)
        if amount < 0:
            raise ValueError("Disbursements cannot be negative.")
        if amount - known[oid]["unusedCommitment"] > 0.01:
            raise ValueError(
                f"{known[oid]['name']} only has "
                f"${known[oid]['unusedCommitment']:,.0f} unused commitment."
            )
        cleaned[oid] = amount
    return cleaned
