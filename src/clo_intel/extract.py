"""Layout extraction: Azure Document Intelligence when configured, else PyMuPDF."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from clo_intel.config import env
from clo_intel.schema import BBox, Citation
from clo_intel.telemetry import LOG


def page_count(path: Path) -> int:
    with pymupdf.open(path) as pdf:
        return pdf.page_count


def render_page_png(path: Path, page_number: int, scale: float = 2.0) -> bytes:
    with pymupdf.open(path) as pdf:
        if page_number < 1 or page_number > pdf.page_count:
            raise ValueError("Page out of range")
        page = pdf.load_page(page_number - 1)
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        return pixmap.tobytes("png")


def locate_quote(path: Path, quote: str) -> list[Citation]:
    hits: list[Citation] = []
    with pymupdf.open(path) as pdf:
        for index, page in enumerate(pdf):
            for rect in page.search_for(quote):
                hits.append(
                    Citation(
                        page=index + 1,
                        quote=quote,
                        bbox=BBox(
                            x0=round(rect.x0 / page.rect.width, 4),
                            y0=round(rect.y0 / page.rect.height, 4),
                            x1=round(rect.x1 / page.rect.width, 4),
                            y1=round(rect.y1 / page.rect.height, 4),
                        ),
                    )
                )
    return hits


def extract_pages(path: Path) -> dict:
    """Raw per-page JSON (text + block boxes). Not yet CLO-meaningful."""
    if env("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"):
        try:
            return _document_intelligence(path)
        except Exception as exc:  # noqa: BLE001 — fall back so local runs still work
            LOG.warning("Document Intelligence failed (%s); using PyMuPDF", exc)
    return _pymupdf_layout(path)


def _pymupdf_layout(path: Path) -> dict:
    pages = []
    with pymupdf.open(path) as pdf:
        for index, page in enumerate(pdf):
            blocks = []
            for block in page.get_text("blocks"):
                x0, y0, x1, y1, text, *_ = block
                if not str(text).strip():
                    continue
                blocks.append(
                    {
                        "text": str(text).strip(),
                        "bbox": {
                            "x0": round(x0 / page.rect.width, 4),
                            "y0": round(y0 / page.rect.height, 4),
                            "x1": round(x1 / page.rect.width, 4),
                            "y1": round(y1 / page.rect.height, 4),
                        },
                    }
                )
            pages.append({"page": index + 1, "text": page.get_text(), "blocks": blocks})
    return {"extractor": "pymupdf_layout", "pages": pages}


def _document_intelligence(path: Path) -> dict:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential
    from azure.identity import DefaultAzureCredential

    endpoint = env("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    key = env("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")
    credential = AzureKeyCredential(key) if key else DefaultAzureCredential()
    client = DocumentIntelligenceClient(endpoint=endpoint, credential=credential)
    with path.open("rb") as fh:
        poller = client.begin_analyze_document("prebuilt-layout", body=fh)
    result = poller.result()
    pages = []
    for page in result.pages or []:
        width = page.width or 1
        height = page.height or 1
        blocks = []
        for line in page.lines or []:
            poly = line.polygon or []
            xs = poly[0::2] or [0]
            ys = poly[1::2] or [0]
            blocks.append(
                {
                    "text": line.content,
                    "bbox": {
                        "x0": round(min(xs) / width, 4),
                        "y0": round(min(ys) / height, 4),
                        "x1": round(max(xs) / width, 4),
                        "y1": round(max(ys) / height, 4),
                    },
                }
            )
        pages.append(
            {
                "page": page.page_number,
                "text": "\n".join(b["text"] for b in blocks),
                "blocks": blocks,
            }
        )
    return {"extractor": "document_intelligence", "pages": pages}
