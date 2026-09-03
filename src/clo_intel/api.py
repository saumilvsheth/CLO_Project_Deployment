from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from clo_intel import review
from clo_intel.extract import page_count, render_page_png
from clo_intel.library import get_document, list_pdfs
from clo_intel.pipeline import run_all
from clo_intel.store import list_runs

WEB = Path(__file__).resolve().parents[2] / "web"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not list_runs() and list_pdfs():
        run_all()
    yield


app = FastAPI(title="CLO Document Intelligence", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")


class ReviewBody(BaseModel):
    action: str
    value: str = ""
    note: str = ""


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.post("/api/pipeline/run")
def trigger_pipeline() -> dict:
    results = run_all()
    return {"documents": [r.document_id for r in results], "fields": sum(len(r.fields) for r in results)}


@app.get("/api/documents")
def documents() -> dict:
    runs = {row["documentId"]: row for row in list_runs()}
    docs = []
    for doc in list_pdfs():
        run = runs.get(doc.id, {})
        docs.append(
            {
                "id": doc.id,
                "title": doc.title,
                "filename": doc.filename,
                "pages": doc.pages,
                "documentType": run.get("documentType", ""),
                "fieldCount": run.get("fieldCount", 0),
            }
        )
    return {"documents": docs}


@app.get("/api/documents/{doc_id}/pages/{page_number}")
def page_image(doc_id: str, page_number: int) -> Response:
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        png = render_page_png(doc.path, page_number)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=png, media_type="image/png")


@app.get("/api/documents/{doc_id}/extractions")
def extractions(doc_id: str) -> dict:
    if not get_document(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    data = review.snapshot(doc_id)
    doc = get_document(doc_id)
    data["pages"] = page_count(doc.path)
    data["title"] = doc.title
    return data


@app.post("/api/reviews/{field_id}")
def review_field(field_id: str, body: ReviewBody) -> dict:
    try:
        return review.apply_review(field_id, body.action, body.value, body.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "pdfs": len(list_pdfs())}
