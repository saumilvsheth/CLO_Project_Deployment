"""Canonical CLO extraction schema. Invalid values never persist silently."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DocumentType(str, Enum):
    indenture = "indenture"
    trustee_report = "trustee_report"
    offering_memorandum = "offering_memorandum"
    rating_report = "rating_report"
    term_sheet = "term_sheet"
    credit_memo = "credit_memo"
    unknown = "unknown"


class BBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class Citation(BaseModel):
    page: int
    quote: str
    bbox: BBox
    confidence: float = 1.0


class ExtractedField(BaseModel):
    id: str
    label: str
    group: str
    value: str
    quote: str
    confidence: float = 1.0
    kind: str = ""
    citations: list[Citation] = Field(default_factory=list)
    needs_review: bool = False
    review_reason: str = ""


class ExtractionResult(BaseModel):
    document_id: str
    document_type: DocumentType
    filename: str
    pages: int
    deal_id: str = ""
    fields: list[ExtractedField]
    warnings: list[str] = Field(default_factory=list)
    extractor: Literal["document_intelligence", "pymupdf_layout"] = "pymupdf_layout"

    @field_validator("fields")
    @classmethod
    def unique_ids(cls, fields: list[ExtractedField]) -> list[ExtractedField]:
        ids = [f.id for f in fields]
        if len(ids) != len(set(ids)):
            raise ValueError("Field ids must be unique")
        return fields


def oc_ratio_out_of_range(value: str) -> bool:
    cleaned = value.replace("%", "").replace(",", "").strip()
    try:
        n = float(cleaned)
    except ValueError:
        return True
    return n < 50 or n > 300
