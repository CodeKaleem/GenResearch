"""Regression tests for repeated citation resolution of stored reports."""
from services.citation_formatting import resolve_and_append_references
from services import pdf_renderer
from services.pdf_renderer import APAPDFRenderer


REGISTRY = [{
    "id": "CR-001",
    "title": "Dermatology Image Classification",
    "authors": "Esteva, A., Kuprel, B., Novoa, R. A.",
    "year": 2017,
}]


def test_resolving_a_resolved_report_is_idempotent():
    raw = "## Introduction\n\nThe model was evaluated in dermatology [CR-001]."
    once = resolve_and_append_references(raw, REGISTRY)

    assert resolve_and_append_references(once, REGISTRY) == once


def test_pdf_resolution_preserves_existing_author_year_citation(monkeypatch):
    resolved = resolve_and_append_references(
        "## Introduction\n\nThe model was evaluated in dermatology [CR-001].",
        REGISTRY,
    )
    observed = []
    original_resolver = pdf_renderer.resolve_and_append_references
    rendered_paragraphs = []
    original_write_paragraph = APAPDFRenderer.write_paragraph

    def capture_resolution(text, citation_registry):
        result = original_resolver(text, citation_registry)
        observed.append(result)
        return result

    def capture_paragraph(self, text):
        rendered_paragraphs.append(text)
        return original_write_paragraph(self, text)

    monkeypatch.setattr(pdf_renderer, "resolve_and_append_references", capture_resolution)
    monkeypatch.setattr(APAPDFRenderer, "write_paragraph", capture_paragraph)
    pdf_bytes = pdf_renderer.render_markdown_to_pdf(
        resolved,
        title="Citation round-trip",
        citation_registry=REGISTRY,
    )

    assert pdf_bytes.startswith(b"%PDF-")
    assert "(Esteva et al., 2017)" in observed[0]
    assert "[CITATION NEEDED]" not in observed[0]
    assert any("(Esteva et al., 2017)" in text for text in rendered_paragraphs)