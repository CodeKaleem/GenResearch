from services.pdf_renderer import render_markdown_to_pdf


def test_pdf_renderer_handles_markdown_lists_and_citations():
    registry = [
        {
            "id": "CR-001",
            "title": "Sample Paper",
            "authors": "Doe, J.",
            "year": 2024,
            "url": "https://example.org/sample",
        }
    ]
    pdf = render_markdown_to_pdf(
        "## Summary\n\n- First item\n- Second item\n\nClaim [CR-001].",
        title="Smoke test",
        citation_registry=registry,
    )

    assert pdf.startswith(b"%PDF-")
