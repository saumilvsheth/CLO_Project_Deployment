"""Human-in-the-loop queue: verify, override, or reject extracted fields."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from threading import Lock

from clo_intel.config import REVIEWS_PATH
from clo_intel.sample_book import deal_for_document, title_for_filename
from clo_intel.store import load_run, list_runs

_lock = Lock()
_MONEY = re.compile(r"^\$[\d,]+(?:\.\d+)?$")
_PERCENT = re.compile(r"^\d+(?:\.\d+)?%$")
_NUMERIC_KINDS = {"money", "oc_ratio", "number", "amount", "percent"}


def _load() -> dict:
    if REVIEWS_PATH.exists():
        return json.loads(REVIEWS_PATH.read_text()).get("reviews", {})
    return {}


def _save(reviews: dict) -> None:
    REVIEWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEWS_PATH.write_text(json.dumps({"reviews": reviews}, indent=2))


def all_reviews() -> dict:
    with _lock:
        return _load()


def is_numeric_field(field: dict) -> bool:
    kind = str(field.get("kind") or "")
    if kind in _NUMERIC_KINDS:
        return True
    if kind:
        return False
    value = str(field.get("value") or "").strip()
    return bool(_MONEY.fullmatch(value) or _PERCENT.fullmatch(value))


def _review_status(field: dict, saved: dict) -> tuple[str, dict]:
    review = saved.get(field["id"]) or {
        "id": field["id"],
        "status": "pending",
        "extracted": field.get("value"),
        "value": field.get("value"),
        "note": "",
        "reviewedAt": None,
    }
    status = review.get("status") or "pending"
    if status == "verified":
        status = "approved"
        review = {**review, "status": "approved"}
    return status, review


def resolution_dashboard() -> dict:
    with _lock:
        saved = _load()
    totals = {"pending": 0, "approved": 0, "overridden": 0, "rejected": 0, "total": 0}
    documents = []
    open_items = []
    closed_items = []
    for row in list_runs():
        run = load_run(row["documentId"])
        if not run:
            continue
        ext = run.get("extraction", {})
        deal = deal_for_document(ext.get("document_id") or row["documentId"])
        title = title_for_filename(ext.get("filename") or f"{row['documentId']}.pdf")
        deal_name = deal.series if deal else ""
        counts = {"pending": 0, "approved": 0, "overridden": 0, "rejected": 0, "total": 0}
        for field in ext.get("fields", []):
            if not is_numeric_field(field):
                continue
            status, review = _review_status(field, saved)
            if status not in totals:
                status = "pending"
            totals[status] += 1
            totals["total"] += 1
            counts[status] += 1
            counts["total"] += 1
            cite = (field.get("citations") or [{}])[0]
            item = {
                "fieldId": field["id"],
                "documentId": row["documentId"],
                "documentType": ext.get("document_type", ""),
                "title": title,
                "dealId": ext.get("deal_id") or (deal.id if deal else ""),
                "dealName": deal_name,
                "label": field.get("label", ""),
                "value": review.get("value") or field.get("value", ""),
                "status": status,
                "confidence": field.get("confidence"),
                "page": cite.get("page"),
                "reviewedAt": review.get("reviewedAt"),
            }
            if status == "pending":
                open_items.append(item)
            else:
                closed_items.append(item)
        if counts["total"]:
            documents.append(
                {
                    "documentId": row["documentId"],
                    "title": title,
                    "dealName": deal_name,
                    "documentType": ext.get("document_type", ""),
                    **counts,
                    "closed": counts["approved"] + counts["overridden"] + counts["rejected"],
                    "open": counts["pending"] > 0,
                }
            )
    open_items.sort(key=lambda item: float(item.get("confidence") or 1))
    closed_items.sort(key=lambda item: item.get("reviewedAt") or "", reverse=True)
    closed = totals["approved"] + totals["overridden"] + totals["rejected"]
    return {
        "totals": {
            **totals,
            "open": totals["pending"],
            "closed": closed,
            "openDocuments": sum(1 for doc in documents if doc["open"]),
            "closedDocuments": sum(1 for doc in documents if not doc["open"]),
        },
        "documents": documents,
        "open": open_items,
        "approved": [item for item in closed_items if item["status"] == "approved"],
        "closed": closed_items,
    }


def snapshot(document_id: str) -> dict:
    run = load_run(document_id)
    if not run:
        return {"items": [], "pending": 0}
    with _lock:
        saved = _load()
    items = []
    pending = 0
    pending_numeric = 0
    for field in run["extraction"]["fields"]:
        review = saved.get(field["id"]) or {
            "id": field["id"],
            "status": "pending",
            "extracted": field["value"],
            "value": field["value"],
            "note": "",
            "reviewedAt": None,
        }
        if review["status"] == "verified":
            review["status"] = "approved"
        if review["status"] == "pending":
            review["value"] = field["value"]
            pending += 1
            if is_numeric_field(field):
                pending_numeric += 1
        items.append({**field, "review": review})
    items.sort(key=lambda item: float(item.get("confidence") or 1))
    deal = deal_for_document(document_id)
    return {
        "documentId": document_id,
        "documentType": run["extraction"].get("document_type"),
        "filename": run["extraction"].get("filename"),
        "pages": run["extraction"].get("pages"),
        "items": items,
        "pending": pending,
        "pendingNumeric": pending_numeric,
        "warnings": run["extraction"].get("warnings", []),
        "dealId": deal.id if deal else "",
        "dealName": deal.series if deal else "",
    }


def apply_review(field_id: str, action: str, value: str = "", note: str = "") -> dict:
    action = action.lower().strip()
    if action not in {"approve", "verify", "override", "reject"}:
        raise ValueError("Action must be approve, override, or reject.")
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
        if action in {"approve", "verify"}:
            row["status"] = "approved"
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
    try:
        from clo_intel.graph import clear_graph_cache

        clear_graph_cache()
    except Exception:  # noqa: BLE001
        pass
    return snapshot(document_id)
