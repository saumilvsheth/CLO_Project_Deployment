from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from clo_intel.config import RUNS_DIR
from clo_intel.schema import ExtractionResult


def save_run(result: ExtractionResult, layout: dict) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNS_DIR / f"{result.document_id}.json"
    payload = {
        "savedAt": datetime.now(timezone.utc).isoformat(),
        "extraction": result.model_dump(mode="json"),
        "layout": layout,
    }
    path.write_text(json.dumps(payload, indent=2))
    return path


def load_run(document_id: str) -> dict | None:
    path = RUNS_DIR / f"{document_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def list_runs() -> list[dict]:
    if not RUNS_DIR.exists():
        return []
    rows = []
    for path in sorted(RUNS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        ext = data.get("extraction", {})
        rows.append(
            {
                "documentId": ext.get("document_id", path.stem),
                "filename": ext.get("filename", ""),
                "documentType": ext.get("document_type", ""),
                "dealId": ext.get("deal_id", ""),
                "pages": ext.get("pages", 0),
                "fieldCount": len(ext.get("fields", [])),
            }
        )
    return rows
