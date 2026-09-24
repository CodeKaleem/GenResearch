"""Typed domain models for the GenResearch pipeline."""

from .schemas import (
    ChunkMetadata,
    ExtractedClaim,
    GeneratedSection,
    PaperProfile,
    ProposalOutput,
    RetrievedChunk,
    VerificationResult,
)

__all__ = [
    "ChunkMetadata",
    "ExtractedClaim",
    "GeneratedSection",
    "PaperProfile",
    "ProposalOutput",
    "RetrievedChunk",
    "VerificationResult",
]