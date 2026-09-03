from __future__ import annotations

from clo_intel.classify import classify
from clo_intel.contextualize import fields_for_document
from clo_intel.extract import extract_pages, page_count
from clo_intel.guardrails import apply_guardrails
from clo_intel.library import Document, list_pdfs
from clo_intel.sample_book import deal_id_for_document
from clo_intel.schema import ExtractionResult
from clo_intel.store import save_run
from clo_intel.telemetry import LOG, configure_logging, set_stage, start_trace


def run_document(doc: Document) -> ExtractionResult:
    configure_logging()
    start_trace(doc.id, "ingest")
    LOG.info("Ingest %s", doc.filename)

    set_stage("classify")
    doc_type = classify(doc.text, doc.filename)
    LOG.info("Classified as %s", doc_type.value)

    set_stage("extract")
    layout = extract_pages(doc.path)
    LOG.info("Extracted %s page(s) via %s", len(layout["pages"]), layout["extractor"])

    set_stage("contextualize")
    fields = fields_for_document(doc.id, doc.path)
    result = ExtractionResult(
        document_id=doc.id,
        document_type=doc_type,
        filename=doc.filename,
        pages=page_count(doc.path),
        deal_id=deal_id_for_document(doc.id),
        fields=fields,
        extractor=layout["extractor"],
    )

    set_stage("guardrails")
    result = apply_guardrails(result)

    set_stage("store")
    save_run(result, layout)
    LOG.info("Saved %s field(s), %s warning(s)", len(result.fields), len(result.warnings))
    return result


def run_all() -> list[ExtractionResult]:
    return [run_document(doc) for doc in list_pdfs()]
