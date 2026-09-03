from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from clo_intel.answer import answer_question
from clo_intel import review
from clo_intel.extract import locate_quote, page_count, render_page_png
from clo_intel.library import get_document, list_pdfs
from clo_intel.sample_book import deal_for_document
from clo_intel.pipeline import run_all
from clo_intel.search import build_index, search as hybrid_search
from clo_intel.store import list_runs

WEB = Path(__file__).resolve().parents[2] / "web"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not list_runs() and list_pdfs():
        run_all()
    build_index()
    yield


app = FastAPI(title="CLO Document Intelligence", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")


class ReviewBody(BaseModel):
    action: str
    value: str = ""
    note: str = ""


class AskBody(BaseModel):
    question: str


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.post("/api/pipeline/run")
def trigger_pipeline() -> dict:
    results = run_all()
    return {"documents": [r.document_id for r in results], "fields": sum(len(r.fields) for r in results)}


@app.get("/api/search")
def search(q: str = "") -> dict:
    return hybrid_search(q)


@app.post("/api/ask")
def ask(body: AskBody) -> dict:
    try:
        return answer_question(body.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/locate")
def locate(doc: str, q: str) -> dict:
    if not get_document(doc):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"documentId": doc, "query": q, "citations": [c.model_dump() for c in locate_quote(get_document(doc).path, q)]}


@app.get("/api/documents")
def documents() -> dict:
    runs = {row["documentId"]: row for row in list_runs()}
    docs = []
    for doc in list_pdfs():
        run = runs.get(doc.id, {})
        deal = deal_for_document(doc.id)
        docs.append(
            {
                "id": doc.id,
                "title": doc.title,
                "filename": doc.filename,
                "pages": doc.pages,
                "documentType": run.get("documentType", ""),
                "dealId": run.get("dealId") or (deal.id if deal else ""),
                "dealName": deal.series if deal else "",
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


@app.get("/api/reviews/dashboard")
def reviews_dashboard() -> dict:
    return review.resolution_dashboard()


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


@app.get("/api/deals/{deal_id}/disbursement")
def deal_disbursement(deal_id: str, pay: str = "") -> dict:
    from clo_intel.waterfall import disbursement_for_deal

    try:
        return disbursement_for_deal(deal_id, pay)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/graph/backfill")
def graph_backfill() -> dict:
    from clo_intel.graph import backfill_graph

    try:
        return backfill_graph()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/graph/neighborhood")
def graph_neighborhood(node: str = "", doc: str = "") -> dict:
    from clo_intel.graph import neighborhood, node_id_for_document

    target = node.strip() or node_id_for_document(doc)
    if not target:
        raise HTTPException(status_code=400, detail="Provide a graph node or document.")
    try:
        return neighborhood(target)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/graph/suggest")
def graph_suggest(q: str = "") -> dict:
    from clo_intel.graph import suggest_nodes

    return {"nodes": suggest_nodes(q)}


@app.get("/api/graph/obligors/{slug}")
def graph_obligor(slug: str) -> dict:
    from clo_intel.graph import deals_holding

    try:
        deals = deals_holding(slug)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"obligor": slug, "deals": deals, "count": len(deals)}


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "pdfs": len(list_pdfs())}
