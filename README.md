# CLO Document Intelligence

Azure-first pipeline for CLO PDFs: ingest → extract (layout + bounding boxes) → map to a canonical schema → validate → human review.

Phase 1 of the architecture in `docs/architecture.md` is implemented locally. GraphRAG and the agent layer are stubs for later phases.

## Run locally

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m clo_intel run
python -m clo_intel serve
```

Open http://127.0.0.1:8000 — review extracted fields against the PDF page they came from (Verify / Edit / Reject).

Sample (fictional) Northbridge CLO PDFs live in `data/pdfs/`.
