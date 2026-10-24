"""Tests for the dedicated multi-source case-study search endpoint."""
import asyncio

from routers import research_search


def test_case_study_search_qualifies_query_and_normalizes_scraper_results(monkeypatch):
    observed = {}

    async def fake_scrape_all_sources(query, use_cache, max_results_per_source):
        observed.update({
            "query": query,
            "use_cache": use_cache,
            "limit": max_results_per_source,
        })
        return [{
            "title": "Solar irrigation field case study",
            "authors": ["A. Researcher", "B. Researcher"],
            "abstract": "A field case study of solar irrigation adoption.",
            "publication_date": "2023-06-01",
            "journal": "Rural Systems",
            "doi": "10.1234/example",
            "url": "https://example.org/study",
            "source": "Crossref",
            "keywords": ["solar irrigation", "smallholder farms"],
        }]

    monkeypatch.setattr(research_search, "scrape_all_sources", fake_scrape_all_sources)
    result = asyncio.run(research_search.search_case_studies(
        research_search.CaseStudySearchRequest(
            topic="solar irrigation in smallholder farms", limit=7
        )
    ))

    assert observed["query"] == "solar irrigation in smallholder farms case study"
    assert observed["limit"] == 7
    assert result["case_studies"][0] == {
        "title": "Solar irrigation field case study",
        "authors": "A. Researcher, B. Researcher",
        "year": 2023,
        "venue": "Rural Systems",
        "abstract": "A field case study of solar irrigation adoption.",
        "doi": "10.1234/example",
        "url": "https://example.org/study",
        "source": "Crossref",
        "keywords": ["solar irrigation", "smallholder farms"],
        "candidate": True,
        "citations": 0,
    }


def test_case_study_query_is_not_duplicated():
    assert research_search._case_study_query("crop adoption case study") == "crop adoption case study"
    assert research_search._case_study_query(" crop adoption case studies ") == "crop adoption case studies"


def test_report_generation_uses_source_ids_and_appends_source_records(monkeypatch):
    observed = {}

    async def fake_call_llm(**kwargs):
        observed.update(kwargs)
        return "## Overview\nAdoption was reported in the supplied abstract [CS-01]."

    monkeypatch.setattr("services.llm_service.call_llm", fake_call_llm)
    result = asyncio.run(research_search.generate_case_study_report(
        research_search.CaseStudyReportRequest(
            topic="Solar irrigation",
            report_type="all",
            studies=[{
                "title": "Solar irrigation field study",
                "authors": "A. Researcher",
                "year": 2023,
                "venue": "Rural Systems",
                "abstract": "The abstract reports increased adoption.",
                "doi": "10.1234/example",
                "url": "https://example.org/study",
                "source": "Crossref",
            }],
        )
    ))

    assert observed["agent_role"] == "summarization"
    assert "CS-01" in observed["prompt"]
    assert "The abstract reports increased adoption." in observed["prompt"]
    assert "### [CS-01] Solar irrigation field study" in result["report"]
    assert "A. Researcher (2023)" in result["report"]
    assert "https://doi.org/10.1234/example" in result["report"]


def test_all_studies_report_appends_every_example_even_if_model_omits_one(monkeypatch):
    async def fake_call_llm(**kwargs):
        return "## Overview\nThe abstracts describe different approaches [CS-01]."

    monkeypatch.setattr("services.llm_service.call_llm", fake_call_llm)
    studies = [
        {"title": "First case", "abstract": "Evidence from first case.", "source": "Crossref"},
        {"title": "Second case", "abstract": "Evidence from second case.", "source": "OpenAlex"},
    ]
    result = asyncio.run(research_search.generate_case_study_report(
        research_search.CaseStudyReportRequest(topic="Water access", studies=studies, report_type="all")
    ))

    assert "[CS-01] First case" in result["report"]
    assert "Evidence from first case." in result["report"]
    assert "[CS-02] Second case" in result["report"]
    assert "Evidence from second case." in result["report"]


def test_single_report_requires_exactly_one_study(monkeypatch):
    async def fake_call_llm(**kwargs):
        return "Summary."

    monkeypatch.setattr("services.llm_service.call_llm", fake_call_llm)
    request = research_search.CaseStudyReportRequest(
        topic="Water access",
        studies=[{"title": "One"}, {"title": "Two"}],
        report_type="single",
    )

    try:
        asyncio.run(research_search.generate_case_study_report(request))
    except Exception as error:
        assert getattr(error, "status_code", None) == 422
    else:
        raise AssertionError("Expected a single-paper request with two studies to be rejected")