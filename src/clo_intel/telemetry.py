from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

_trace: ContextVar[str] = ContextVar("trace_id", default="")
_doc: ContextVar[str] = ContextVar("document_id", default="")
_stage: ContextVar[str] = ContextVar("pipeline_stage", default="")

LOG = logging.getLogger("clo_intel")


class _Formatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.trace_id = _trace.get() or "-"
        record.document_id = _doc.get() or "-"
        record.pipeline_stage = _stage.get() or "-"
        return super().format(record)


def configure_logging() -> None:
    if LOG.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        _Formatter("%(asctime)s %(levelname)s stage=%(pipeline_stage)s doc=%(document_id)s trace=%(trace_id)s %(message)s")
    )
    LOG.addHandler(handler)
    LOG.setLevel(logging.INFO)


def start_trace(document_id: str, stage: str) -> str:
    trace_id = uuid.uuid4().hex[:12]
    _trace.set(trace_id)
    _doc.set(document_id)
    _stage.set(stage)
    return trace_id


def set_stage(stage: str) -> None:
    _stage.set(stage)
