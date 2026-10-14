"""Chunk parsed PDF blocks while retaining provenance metadata."""
from __future__ import annotations

import hashlib

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings
from models.schemas import ChunkMetadata
from .pdf_parser import ParsedBlock


def _merge_blocks_for_chunking(blocks: list[ParsedBlock], max_merge_len: int = 1000) -> list[ParsedBlock]:
    """
    Merge small adjacent blocks from the same page and section heading before splitting,
    so author lines, affiliations, and header metadata are never split into isolated fragments.
    """
    if not blocks:
        return []
    merged: list[ParsedBlock] = []
    current = blocks[0]

    for next_block in blocks[1:]:
        same_page = current.page == next_block.page
        same_heading = current.section_heading == next_block.section_heading
        is_page1_header = current.page == 1 and (
            current.section_heading in {"Title & Authors", None}
            or next_block.section_heading in {"Title & Authors", None}
        )

        can_merge = (
            not current.is_table
            and not next_block.is_table
            and same_page
            and (same_heading or is_page1_header)
            and (len(current.text) + len(next_block.text) + 2 <= max_merge_len)
        )
        if can_merge:
            combined_text = current.text.rstrip() + "\n\n" + next_block.text.lstrip()
            heading = current.section_heading or next_block.section_heading or ("Title & Authors" if current.page == 1 else None)
            current = ParsedBlock(
                text=combined_text,
                page=current.page,
                section_heading=heading,
                is_table=False,
                table_data=None,
            )
        else:
            merged.append(current)
            current = next_block
    merged.append(current)
    return merged


def chunk_document(
    blocks: list[ParsedBlock],
    paper_id: str,
    title: str | None = None,
) -> list[tuple[ChunkMetadata, str]]:
    """Create deterministic, provenance-aware chunks from parsed blocks."""
    coalesced_blocks = _merge_blocks_for_chunking(blocks, max_merge_len=settings.CHUNK_SIZE)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "],
        length_function=len,
    )
    chunks: list[tuple[ChunkMetadata, str]] = []
    for block_index, block in enumerate(coalesced_blocks):
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