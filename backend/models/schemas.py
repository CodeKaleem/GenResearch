"""Single-source-of-truth Pydantic contracts for research generation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    chunk_id: str
    paper_id: str
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    section_heading: str | None = None
    page: int | None = None
    chunk_index: int
    char_start: int | None = None
    char_end: int | None = None
    is_table: bool = False
    table_data: dict | None = None


class RetrievedChunk(ChunkMetadata):
    text: str
    score: float


class ExtractedClaim(BaseModel):
    claim_id: str
    text: str
    cited_chunk_ids: list[str] = Field(default_factory=list)
    section: str


class VerificationResult(BaseModel):
    claim_id: str
    verdict: Literal["supported", "unsupported", "partial"]
    discrepancy: str | None = None
    corrected_text: str | None = None


class PaperProfile(BaseModel):
    paper_id: str
    paper_type: Literal["review", "empirical", "theoretical", "other"] = "other"
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    key_figures: list[str] = Field(default_factory=list)


class GeneratedSection(BaseModel):
    section_name: str
    text: str
    claims: list[ExtractedClaim] = Field(default_factory=list)
    verification: list[VerificationResult] = Field(default_factory=list)
    verified: bool = False


class ProposalOutput(BaseModel):
    topic: str
    sections: list[GeneratedSection] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    figures: list[str] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)
    human_input_needed: list[str] = Field(default_factory=list)
    quality_report: dict = Field(default_factory=dict)
    session_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))