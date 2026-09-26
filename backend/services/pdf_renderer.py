# ============================================================
# GenResearch — PDF Renderer (C3)
# Renders markdown into an APA 7-style academic PDF with Times,
# double spacing, APA headings and references, and page numbers.
# ============================================================
from __future__ import annotations

import re

from fpdf import FPDF

from services.citation_formatting import resolve_and_append_references

FONT = "times"
BODY_PT = 12
MARGIN_MM = 25.4
INDENT_MM = 12.7


def _pt_to_mm_line_height(size_pt: float, spacing: float) -> float:
    """Convert point size and spacing multiplier to a millimeter line height."""
    return size_pt * 0.3528 * spacing


class APAPDFRenderer(FPDF):
    def __init__(self, title: str, double_spaced: bool = True):
        super().__init__(format="Letter", unit="mm")
        self.doc_title = title
        self.spacing = 2.0 if double_spaced else 1.15
        self.line_h = _pt_to_mm_line_height(BODY_PT, self.spacing)
        self.set_margins(MARGIN_MM, MARGIN_MM, MARGIN_MM)
        self.set_auto_page_break(auto=True, margin=MARGIN_MM)
        self.set_font(FONT, size=BODY_PT)
        self._in_body = False
        self.add_page()
        self._render_title_page()
        self._in_body = True
        self.add_page()

    def header(self):
        if not self._in_body:
            return
        self.set_font(FONT, size=10)
        self.set_xy(-self.r_margin - 25, 10)
        self.cell(25, 6, str(self.page_no()), align="R")
        self.set_font(FONT, size=BODY_PT)

    def footer(self):
        pass

    def _render_title_page(self):
        self.set_font(FONT, "B", BODY_PT)
        self.ln(60)
        self.multi_cell(0, self.line_h, self.doc_title, align="C")

    def write_heading(self, text: str, level: int):
        self.ln(self.line_h * 0.4)
        if level <= 1:
            self.set_font(FONT, "B", BODY_PT)
            self.multi_cell(0, self.line_h, text, align="C")
        elif level == 2:
            self.set_font(FONT, "B", BODY_PT)
            self.multi_cell(0, self.line_h, text, align="L")
        else:
            self.set_font(FONT, "BI", BODY_PT)
            self.multi_cell(0, self.line_h, text, align="L")
        self.set_font(FONT, size=BODY_PT)

    def write_paragraph(self, text: str):
        """Write a ragged-right paragraph with an APA first-line indent."""
        self.set_font(FONT, size=BODY_PT)
        self.set_x(self.l_margin + INDENT_MM)
        segments = re.split(r"(\*\*[^*]+\*\*)", text)
        for segment in segments:
            if not segment:
                continue
            if segment.startswith("**") and segment.endswith("**"):
                self.set_font(FONT, "B", BODY_PT)
                self.write(self.line_h, segment[2:-2])
            else:
                self.set_font(FONT, size=BODY_PT)
                self.write(self.line_h, segment)
        self.ln(self.line_h)

    def _wrap_hanging(self, text: str, first_width: float, cont_width: float) -> list[str]:
        """Word-wrap text with a narrower width after the first line."""
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            limit = first_width if not lines else cont_width
            if self.get_string_width(candidate) <= limit:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def write_reference(self, text: str):
        """Write one reference entry using a 0.5-inch hanging indent."""
        self.set_font(FONT, size=BODY_PT)
        full_width = self.w - self.l_margin - self.r_margin
        lines = self._wrap_hanging(text, full_width, full_width - INDENT_MM)
        for index, line in enumerate(lines):
            self.set_x(self.l_margin + (INDENT_MM if index > 0 else 0))
            self.cell(0, self.line_h, line, new_x="LMARGIN", new_y="NEXT")
        self.ln(self.line_h * 0.15)


def _clean_inline_markdown_noise(text: str) -> str:
    """Convert markdown list markers to a Times-core-font-safe marker."""
    return re.sub(r"^\s*[-*]\s+", "- ", text)


def render_markdown_to_pdf(
    markdown_text: str,
    title: str = "Research Document",
    citation_registry: list[dict] | None = None,
    double_spaced: bool = True,
) -> bytes:
    """Render markdown into an APA-styled PDF, resolving citations if provided."""
    if citation_registry:
        markdown_text = resolve_and_append_references(markdown_text, citation_registry)

    pdf = APAPDFRenderer(title=title, double_spaced=double_spaced)

    for block in re.split(r"\n\s*\n", markdown_text.strip()):
        block = block.strip()
        if not block:
            continue

        if block.startswith("### "):
            pdf.write_heading(block[4:].strip(), level=3)
        elif block.startswith("## "):
            heading_text = block[3:].strip()
            pdf.write_heading(
                "References" if heading_text.lower() == "references" else heading_text,
                level=1 if heading_text.lower() == "references" else 2,
            )
        elif block.startswith("# "):
            pdf.write_heading(block[2:].strip(), level=1)
        else:
            lines = block.split("\n")
            is_reference_block = all(
                re.match(r"^[A-Z].*\(\d{4}[a-z]?\)\.|^\(.*\d{4}.*\)", line.strip())
                for line in lines
                if line.strip()
            )
            if is_reference_block:
                for line in lines:
                    if line.strip():
                        pdf.write_reference(_clean_inline_markdown_noise(line.strip()))
            else:
                paragraph = _clean_inline_markdown_noise(block.replace("\n", " "))
                pdf.write_paragraph(paragraph)

    return bytes(pdf.output())
