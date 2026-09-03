from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from clo_intel.config import PDF_DIR
from clo_intel.sample_book import document_sort_key, title_for_filename


@dataclass
class Document:
    id: str
    filename: str
    title: str
    pages: int
    text: str
    path: Path
    page_texts: list[str]


def list_pdfs() -> list[Document]:
    docs: list[Document] = []
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(PDF_DIR.glob("*.pdf"), key=lambda p: document_sort_key(p.name)):
        reader = PdfReader(str(path))
        page_texts = [(page.extract_text() or "") for page in reader.pages]
        docs.append(
            Document(
                id=path.stem,
                filename=path.name,
                title=title_for_filename(path.name),
                pages=len(reader.pages),
                text="\n\n".join(page_texts),
                path=path,
                page_texts=page_texts,
            )
        )
    return docs


def get_document(doc_id: str) -> Document | None:
    for doc in list_pdfs():
        if doc.id == doc_id:
            return doc
    return None
