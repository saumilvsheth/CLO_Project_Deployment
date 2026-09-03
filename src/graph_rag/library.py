"""Load and search the sample CLO PDFs on disk."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "data" / "pdfs"

TITLES = {
    "northbridge-clo-2024-1-term-sheet.pdf": "Preliminary term sheet",
    "northbridge-clo-2024-1-apex-credit-memo.pdf": "Apex Industrial credit memorandum",
    "northbridge-clo-2024-1-monthly-report-aug-2024.pdf": "August 2024 monthly trustee report",
}


@dataclass
class Document:
    id: str
    filename: str
    title: str
    pages: int
    text: str
    path: Path
    page_texts: list[str]


_CACHE: list[Document] | None = None


def pdf_dir() -> Path:
    return PDF_DIR


def load_documents() -> list[Document]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    docs: list[Document] = []
    for path in sorted(PDF_DIR.glob("*.pdf")):
        reader = PdfReader(str(path))
        page_texts = [(page.extract_text() or "") for page in reader.pages]
        text = "\n\n".join(page_texts)
        docs.append(
            Document(
                id=path.stem,
                filename=path.name,
                title=TITLES.get(path.name, path.stem.replace("-", " ")),
                pages=len(reader.pages),
                text=text,
                path=path,
                page_texts=page_texts,
            )
        )
    _CACHE = docs
    return docs


def get_document(doc_id: str) -> Document | None:
    for doc in load_documents():
        if doc.id == doc_id:
            return doc
    return None


def search_documents(query: str, limit: int = 12) -> list[dict]:
    needle = query.strip().lower()
    if not needle:
        return []
    hits: list[dict] = []
    for doc in load_documents():
        for page_no, page_text in enumerate(doc.page_texts, start=1):
            lower = page_text.lower()
            start = 0
            while True:
                idx = lower.find(needle, start)
                if idx < 0:
                    break
                left = max(0, idx - 90)
                right = min(len(page_text), idx + len(needle) + 90)
                snippet = page_text[left:right].replace("\n", " ").strip()
                hits.append(
                    {
                        "documentId": doc.id,
                        "title": doc.title,
                        "filename": doc.filename,
                        "page": page_no,
                        "snippet": snippet,
                    }
                )
                if len(hits) >= limit:
                    return hits
                start = idx + len(needle)
    return hits
