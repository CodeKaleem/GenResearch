"""Chunk parsed PDF blocks while retaining provenance metadata."""
from __future__ import annotations

import hashlib

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings
from models.schemas import ChunkMetadata
from .pdf_parser import ParsedBlock


def chunk_document(
    blocks: list[ParsedBlock],
    paper_id: str,
    title: str | None = None,
) -> list[tuple[ChunkMetadata, str]]:
    """Create deterministic, provenance-aware chunks from parsed blocks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "],
        length_function=len,
    )
    chunks: list[tuple[ChunkMetadata, str]] = []
    for block_index, block in enumerate(blocks):
        for local_index, text in enumerate(splitter.split_text(block.text)):
            seed = f"{paper_id}:{block.page}:{block_index}:{local_index}:{text}"
            chunk_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                paper_id=paper_id,
                title=title,
                section_heading=block.section_heading,
                page=block.page,
                chunk_index=len(chunks),
                is_table=block.is_table,
                table_data=block.table_data,
            )
            chunks.append((metadata, text))
    return chunks