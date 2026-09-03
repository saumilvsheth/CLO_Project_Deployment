"""Find quoted text in a PDF and return page-relative bounding boxes."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from graph_rag.library import get_document


def locate_quote(pdf_path: Path, quote: str) -> list[dict]:
    """Return every place `quote` appears, with boxes as 0–1 fractions of the page."""
    hits: list[dict] = []
    with pymupdf.open(pdf_path) as pdf:
        for index, page in enumerate(pdf):
            for rect in page.search_for(quote):
                hits.append(
                    {
                        "page": index + 1,
                        "quote": quote,
                        "bbox": {
                            "x0": round(rect.x0 / page.rect.width, 4),
                            "y0": round(rect.y0 / page.rect.height, 4),
                            "x1": round(rect.x1 / page.rect.width, 4),
                            "y1": round(rect.y1 / page.rect.height, 4),
                        },
                    }
                )
    return hits


def render_page_png(pdf_path: Path, page_number: int, scale: float = 2.0) -> bytes:
    with pymupdf.open(pdf_path) as pdf:
        if page_number < 1 or page_number > pdf.page_count:
            raise ValueError("Page out of range")
        page = pdf.load_page(page_number - 1)
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        return pixmap.tobytes("png")


def page_count(pdf_path: Path) -> int:
    with pymupdf.open(pdf_path) as pdf:
        return pdf.page_count


def locate_in_document(doc_id: str, quote: str) -> list[dict]:
    doc = get_document(doc_id)
    if not doc:
        return []
    return locate_quote(doc.path, quote)
