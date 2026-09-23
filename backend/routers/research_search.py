"""Public academic paper discovery endpoint."""
from __future__ import annotations

import asyncio
import re
from difflib import SequenceMatcher

import aiohttp
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services.pdf_extractor import extract_text_from_pdf
from services.source_gathering import (
    API_TIMEOUT,
    search_arxiv,
    search_crossref,
    search_openalex,
    search_semantic_scholar,
)

router = APIRouter(tags=["research search"])


async def _query_from_document(document: UploadFile) -> str:
    if not document.filename or not document.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    text = await extract_text_from_pdf(await document.read())
    query = re.sub(r"\s+", " ", text).strip()
    if not query:
        query = document.filename.rsplit(".", 1)[0].replace("_", " ")
    return query[:1200]


def _normalize(items: list[dict], source: str) -> list[dict]:
    normalized = []
    for item in items:
        normalized.append({
            "title": item.get("title", "Untitled"),
            "authors": item.get("authors") or "Unknown authors",
            "venue": item.get("venue") or source.replace("_", " ").title(),
            "year": item.get("year"),
            "abstract": item.get("abstract_snippet") or "Abstract unavailable.",
            "citations": item.get("citation_count") or 0,
            "url": item.get("url", ""),
            "source": source,
        })
    return normalized


def _dedupe_and_rank(papers: list[dict], limit: int) -> list[dict]:
    kept: list[dict] = []
    for paper in papers:
        normalized = re.sub(r"[^a-z0-9]+", " ", paper["title"].lower()).strip()
        match = next((existing for existing in kept if SequenceMatcher(None, normalized, existing["_title"]).ratio() >= 0.9), None)
        if match is None:
            paper["_title"] = normalized
            kept.append(paper)
        elif paper["citations"] > match["citations"]:
            paper["_title"] = normalized
            kept[kept.index(match)] = paper
    kept.sort(key=lambda paper: paper["citations"] + ((paper["year"] or 0) * 2), reverse=True)
    for paper in kept:
        paper.pop("_title", None)
    return kept[:limit]


@router.post("/search-papers")
async def search_papers(
    mode: str = Form(...),
    topic: str | None = Form(None),
    num_papers: int = Form(5),
    document: UploadFile | None = File(None),
):
    if mode not in {"topic", "document"}:
        raise HTTPException(status_code=400, detail="Mode must be topic or document.")
    query = await _query_from_document(document) if mode == "document" and document else (topic or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Enter a topic or upload a document.")

    limit = max(1, min(20, num_papers))
    async with aiohttp.ClientSession(timeout=API_TIMEOUT) as session:
        responses = await asyncio.gather(
            search_semantic_scholar(query, limit=limit, session=session),
            search_arxiv(query, limit=limit, session=session),
            search_crossref(query, limit=limit, session=session),
            search_openalex(query, limit=limit, session=session),
        )
    papers = [paper for response, source in zip(responses, ("semantic_scholar", "arxiv", "crossref", "openalex")) for paper in _normalize(response.get("results", []), source)]
    return {"query": query, "papers": _dedupe_and_rank(papers, limit)}