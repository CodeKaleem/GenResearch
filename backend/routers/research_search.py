"""Public academic paper discovery endpoint."""
from __future__ import annotations

import asyncio
import json
import re
from difflib import SequenceMatcher
from typing import Literal

import aiohttp
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from config import settings
from services.pdf_extractor import extract_text_from_pdf
from services.scraping_engine import scrape_all_sources
from services.source_gathering import (
    API_TIMEOUT,
    search_arxiv,
    search_crossref,
    search_openalex,
    search_semantic_scholar,
)

router = APIRouter(tags=["research search"])
MAX_DISCOVERY_DOCUMENT_BYTES = 25 * 1024 * 1024


class CaseStudySearchRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=1200)
    limit: int = Field(default=10, ge=1, le=20)


class CaseStudyReportSource(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    authors: str = Field(default="Unknown authors", max_length=1000)
    year: int | None = None
    venue: str = Field(default="", max_length=500)
    abstract: str = Field(default="", max_length=3000)
    doi: str = Field(default="", max_length=300)
    url: str = Field(default="", max_length=2000)
    source: str = Field(default="Unknown source", max_length=200)


class CaseStudyReportRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=1200)
    studies: list[CaseStudyReportSource] = Field(min_length=1, max_length=20)
    report_type: Literal["single", "all"] = "all"


def _case_study_query(topic: str) -> str:
    normalized = re.sub(r"\s+", " ", topic).strip()
    if re.search(r"\bcase stud(?:y|ies)\b", normalized, re.IGNORECASE):
        return normalized
    return f"{normalized} case study"


async def _query_from_document(document: UploadFile) -> str:
    if not document.filename or not document.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    file_bytes = await document.read()
    if len(file_bytes) > MAX_DISCOVERY_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Discovery PDFs must be 25 MB or smaller.")
    text = await extract_text_from_pdf(file_bytes)
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

    if getattr(settings, "ENABLE_SCRAPING_PIPELINE", True) and len(papers) < limit:
        try:
            scraped = await scrape_all_sources(query, use_cache=getattr(settings, "SCRAPER_USE_CACHE", True), max_results_per_source=limit)
            for sp in scraped:
                date_str = str(sp.get("publication_date") or "")
                year_match = re.search(r"\b(19\d\d|20\d\d)\b", date_str)
                parsed_year = int(year_match.group(1)) if year_match else None
                authors_str = ", ".join(sp.get("authors") or []) if isinstance(sp.get("authors"), list) else str(sp.get("authors") or "Unknown authors")
                papers.append({
                    "title": sp.get("title", "Untitled"),
                    "authors": authors_str,
                    "venue": sp.get("source", "Web Scraper"),
                    "year": parsed_year,
                    "abstract": sp.get("abstract") or "Abstract unavailable.",
                    "citations": 0,
                    "url": sp.get("url", ""),
                    "source": sp.get("source", "").lower(),
                })
        except Exception:
            pass

    return {"query": query, "papers": _dedupe_and_rank(papers, limit)}


@router.post("/search-case-studies")
async def search_case_studies(req: CaseStudySearchRequest):
    """Gather case-study candidates from the configured multi-source scrapers."""
    topic = re.sub(r"\s+", " ", req.topic).strip()
    query = _case_study_query(topic)

    try:
        scraped = await scrape_all_sources(
            query,
            use_cache=settings.SCRAPER_USE_CACHE,
            max_results_per_source=req.limit,
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail="Case-study search is temporarily unavailable.") from error

    candidates = []
    for item in scraped:
        publication_date = str(item.get("publication_date") or "")
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", publication_date)
        authors = item.get("authors") or []
        candidates.append({
            "title": item.get("title") or "Untitled study",
            "authors": ", ".join(authors) if isinstance(authors, list) else str(authors),
            "year": int(year_match.group(1)) if year_match else None,
            "venue": item.get("journal") or item.get("venue") or "",
            "abstract": item.get("abstract") or "Abstract unavailable from this source.",
            "doi": item.get("doi") or "",
            "url": item.get("url") or "",
            "source": item.get("source") or "Unknown source",
            "keywords": item.get("keywords") or [],
            "candidate": True,
        })

    ranked = _dedupe_and_rank(
        [{**candidate, "citations": 0} for candidate in candidates], req.limit
    )
    return {"topic": topic, "query": query, "case_studies": ranked}


@router.post("/generate-case-study-report")
async def generate_case_study_report(req: CaseStudyReportRequest):
    """Create a cited synthesis using only metadata and abstracts from search results."""
    from services.llm_service import call_llm

    if req.report_type == "single" and len(req.studies) != 1:
        raise HTTPException(status_code=422, detail="A single-paper summary requires exactly one study.")

    source_records = []
    for index, study in enumerate(req.studies, start=1):
        source_records.append({
            "citation_id": f"CS-{index:02d}",
            "title": study.title,
            "authors": study.authors,
            "year": study.year,
            "venue": study.venue,
            "abstract": study.abstract[:600],
        })

    if req.report_type == "single":
        writing_instruction = (
            "Write a concise structured summary of this one study: purpose or context, "
            "approach, reported findings, and limitations, but only where the supplied "
            "abstract supports those details. Cite factual statements with [CS-01]."
        )
    else:
        writing_instruction = (
            "Write a general report with an overview, cross-study themes and contrasts, and "
            "a concise discussion. Mention and cite EVERY supplied study at least once using "
            "its exact [CS-##] ID. Include a short subsection for each study, and compare "
            "findings only when the abstracts support the comparison."
        )

    prompt = (
        f"Research topic or description: {req.topic.strip()}\n\n"
        "Searched source records (the abstract is the only study content available):\n"
        f"{json.dumps(source_records, ensure_ascii=True, indent=2)}\n\n"
        f"{writing_instruction} Do not invent locations, sample sizes, methods, outcomes, "
        "dates, or causal claims. If an abstract does not establish that a record is a case "
        "study, describe it as a related study rather than a confirmed case study. Do not "
        "create a reference list; source evidence will be appended separately."
    )
    report = await call_llm(
        prompt=prompt,
        agent_role="summarization",
        system=(
            "You are an evidence-grounded academic research writer. Use only details explicitly "
            "present in the supplied source records. Be clear when evidence is incomplete. "
            "Return readable Markdown and no fabricated citations."
        ),
        temperature=0.1,
        max_tokens=2800,
    )

    examples = ["## Individual study examples and source evidence"]
    for index, study in enumerate(req.studies, start=1):
        citation_id = f"CS-{index:02d}"
        example = f"### [{citation_id}] {study.title}\n{study.authors} ({study.year or 'n.d.'})"
        if study.venue:
            example += f" · {study.venue}"
        example += f" · Source: {study.source}\n\n"
        example += study.abstract.strip() or "Abstract unavailable; consult the linked source for details."
        link = study.doi or study.url
        if link:
            example += f"\n\nSource link: {link if link.startswith('http') else f'https://doi.org/{link}'}"
        examples.append(example)

    return {
        "topic": req.topic.strip(),
        "report_type": req.report_type,
        "report": f"{report.strip()}\n\n" + "\n\n".join(examples),
    }