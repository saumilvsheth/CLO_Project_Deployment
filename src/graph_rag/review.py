"""Human-in-the-loop review of extracted fields: verify, edit, or reject."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from graph_rag.extract import extract_fields

STORE = Path(__file__).resolve().parents[2] / "data" / "reviews.json"
_lock = Lock()


def _blank_review(field: dict) -> dict:
    return {
        "id": field["id"],
        "status": "pending",
        "extracted": field["extracted"],
        "value": field["extracted"],
        "note": "",
        "reviewedAt": None,
    }


def _load() -> dict:
    extracted = extract_fields()
    by_id = {item["id"]: item for item in extracted}
    saved: dict = {}
    if STORE.exists():
        saved = json.loads(STORE.read_text()).get("reviews", {})
    reviews = {}
    for field_id, field in by_id.items():
        row = saved.get(field_id) or _blank_review(field)
        # Keep the latest extractor output; preserve human edits.
        row["extracted"] = field["extracted"]
        if row["status"] == "pending":
            row["value"] = field["extracted"]
        reviews[field_id] = row
    return {"fields": extracted, "reviews": reviews}


def _save(reviews: dict) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps({"reviews": reviews}, indent=2))


def snapshot(document_id: str | None = None) -> dict:
    with _lock:
        state = _load()
    items = []
    pending = 0
    for field in state["fields"]:
        if document_id and field["documentId"] != document_id:
            continue
        review = state["reviews"][field["id"]]
        if review["status"] == "pending":
            pending += 1
        items.append({**field, "review": review})
    return {"items": items, "pending": pending}


def apply_review(field_id: str, action: str, value: str | None = None, note: str = "") -> dict:
    action = action.lower().strip()
    if action not in {"verify", "override", "reject"}:
        raise ValueError("Action must be verify, override, or reject.")
    with _lock:
        state = _load()
        if field_id not in state["reviews"]:
            raise ValueError(f"Unknown field: {field_id}")
        row = state["reviews"][field_id]
        now = datetime.now(timezone.utc).isoformat()
        if action == "verify":
            row["status"] = "verified"
            row["value"] = row["extracted"]
        elif action == "override":
            if not (value or "").strip():
                raise ValueError("Provide a replacement value to override.")
            row["status"] = "overridden"
            row["value"] = value.strip()
        else:
            row["status"] = "rejected"
        row["note"] = note.strip()
        row["reviewedAt"] = now
        _save(state["reviews"])
    return snapshot()
