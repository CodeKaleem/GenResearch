"""Regression coverage for unresolved figure placeholders in PDF output."""
from services.pdf_renderer import _strip_figure_placeholders, render_markdown_to_pdf


def test_figure_placeholder_cleanup_handles_single_and_double_brackets():
    text = "Some text [FIGURE:id] more text [[FIGURE:figure-2]] end."
    cleaned = _strip_figure_placeholders(text)
    assert "FIGURE" not in cleaned
    assert all(fragment in cleaned for fragment in ("Some text", "more text", "end."))


def test_figure_placeholder_cleanup_removes_common_aside():
    cleaned = _strip_figure_placeholders(
        "A claim here. [FIGURE:id] (Placeholder for a figure if necessary)"
    )
    assert "FIGURE" not in cleaned
    assert "Placeholder" not in cleaned


def test_pdf_renders_when_draft_contains_figure_placeholders():
    registry = [{"id": "CR-001", "title": "A Paper", "authors": "Doe, J.", "year": 2020}]
    draft = (
        "## Introduction\n\nA claim here [CR-001]. [FIGURE:id]\n\n"
        "## Results\n\nMore text. [[FIGURE:figure-2]] "
        "(Placeholder for a figure if necessary)\n"
    )
    pdf_bytes = render_markdown_to_pdf(draft, title="test", citation_registry=registry)
    assert pdf_bytes.startswith(b"%PDF-")
