"""Human-in-the-loop queue: verify, override, or reject extracted fields."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from threading import Lock

from clo_intel.config import REVIEWS_PATH
from clo_intel.store import load_run, list_runs

_lock = Lock()


def _load() -> dict:
    if REVIEWS_PATH.exists():
        return json.loads(REVIEWS_PATH.read_text()).get("reviews", {})
    return {}


def _save(reviews: dict) -> None:
    REVIEWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEWS_PATH.write_text(json.dumps({"reviews": reviews}, indent=2))


def snapshot(document_id: str) -> dict:
    run = load_run(document_id)
    if not run:
        return {"items": [], "pending": 0}
    with _lock:
        saved = _load()
    items = []
    pending = 0
    for field in run["extraction"]["fields"]:
        review = saved.get(field["id"]) or {
            "id": field["id"],
            "status": "pending",
            "extracted": field["value"],
            "value": field["value"],
            "note": "",
            "reviewedAt": None,
        }
        if review["status"] == "pending":
            review["value"] = field["value"]
            pending += 1
        items.append({**field, "review": review})
    return {
        "documentId": document_id,
        "documentType": run["extraction"].get("document_type"),
        "filename": run["extraction"].get("filename"),
        "pages": run["extraction"].get("pages"),
        "items": items,
        "pending": pending,
        "warnings": run["extraction"].get("warnings", []),
    }


def apply_review(field_id: str, action: str, value: str = "", note: str = "") -> dict:
    action = action.lower().strip()
    if action not in {"verify", "override", "reject"}:
        raise ValueError("Action must be verify, override, or reject.")
    document_id = None
    extracted = None
    for row in list_runs():
        run = load_run(row["documentId"])
        for field in run["extraction"]["fields"]:
            if field["id"] == field_id:
                document_id = row["documentId"]
                extracted = field["value"]
                break
        if document_id:
            break
    if not document_id:
        raise ValueError(f"Unknown field: {field_id}")
    with _lock:
        reviews = _load()
        row = reviews.get(field_id) or {"id": field_id}
        row["extracted"] = extracted
        row["reviewedAt"] = datetime.now(timezone.utc).isoformat()
        row["note"] = note.strip()
        if action == "verify":
            row["status"] = "verified"
            row["value"] = extracted
        elif action == "override":
            if not value.strip():
                raise ValueError("Provide a replacement value to override.")
            row["status"] = "overridden"
            row["value"] = value.strip()
        else:
            row["status"] = "rejected"
        reviews[field_id] = row
        _save(reviews)
    return snapshot(document_id)
