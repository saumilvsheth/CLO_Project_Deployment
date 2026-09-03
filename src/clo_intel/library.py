from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from clo_intel.config import PDF_DIR

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


def list_pdfs() -> list[Document]:
    docs: list[Document] = []
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(PDF_DIR.glob("*.pdf")):
        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
        docs.append(
            Document(
                id=path.stem,
                filename=path.name,
                title=TITLES.get(path.name, path.stem.replace("-", " ")),
                pages=len(reader.pages),
                text="\n\n".join(pages),
                path=path,
            )
        )
    return docs


def get_document(doc_id: str) -> Document | None:
    for doc in list_pdfs():
        if doc.id == doc_id:
            return doc
    return None
