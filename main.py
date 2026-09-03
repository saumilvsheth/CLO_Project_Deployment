"""Northbridge CLO credit desk — documents and obligor disbursements."""

from __future__ import annotations

from pathlib import Path
import sys

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from graph_rag import disburse, review
from graph_rag.citations import locate_in_document, page_count, render_page_png
from graph_rag.library import get_document, load_documents, pdf_dir, search_documents
WEB = ROOT / "web"

app = FastAPI(title="Northbridge CLO desk")
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")


class ReviewRequest(BaseModel):
    action: str
    value: str = ""
    note: str = ""


class DisburseRequest(BaseModel):
    amounts: dict[str, float] = Field(default_factory=dict)
    memo: str = ""
    pool: float | None = None
    method: str = "custom"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/api/search")
def search(q: str = "") -> dict:
    return {"hits": search_documents(q)}


@app.get("/api/documents")
def list_documents() -> dict:
    docs = [
        {
            "id": doc.id,
            "title": doc.title,
            "filename": doc.filename,
            "pages": doc.pages,
        }
        for doc in load_documents()
    ]
    return {"documents": docs}


@app.get("/api/documents/{doc_id}")
def read_document(doc_id: str) -> dict:
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": doc.id,
        "title": doc.title,
        "filename": doc.filename,
        "pages": doc.pages,
        "text": doc.text,
    }


@app.get("/api/documents/{doc_id}/file")
def download_document(doc_id: str) -> FileResponse:
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(doc.path, media_type="application/pdf", filename=doc.filename)


@app.get("/api/documents/{doc_id}/pages/{page_number}")
def document_page(doc_id: str, page_number: int) -> Response:
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        png = render_page_png(doc.path, page_number)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=png, media_type="image/png")


@app.get("/api/documents/{doc_id}/extractions")
def document_extractions(doc_id: str) -> dict:
    if not get_document(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    data = review.snapshot(doc_id)
    data["pages"] = page_count(get_document(doc_id).path)
    return data


@app.post("/api/reviews/{field_id}")
def review_field(field_id: str, body: ReviewRequest) -> dict:
    try:
        return review.apply_review(field_id, body.action, body.value, body.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/locate")
def locate(doc: str, q: str) -> dict:
    return {"documentId": doc, "query": q, "citations": locate_in_document(doc, q)}


@app.get("/api/book")
def book() -> dict:
    return disburse.snapshot()


@app.post("/api/disbursements/preview")
def preview(body: DisburseRequest) -> dict:
    amounts = body.amounts
    if body.method == "prorata":
        pool = body.pool if body.pool is not None else disburse.snapshot()["fundingRemaining"]
        amounts = disburse.prorata_amounts(pool)
    try:
        return disburse.preview(amounts)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/disbursements")
def create_disbursement(body: DisburseRequest) -> dict:
    try:
        return disburse.commit(body.amounts, body.memo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "pdfs": pdf_dir().exists()}
