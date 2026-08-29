# ============================================================
# GenResearch — PDF Renderer (C3)
# On-demand PDF generation from Markdown using fpdf2.
# ============================================================
import markdown
from fpdf import FPDF
from io import BytesIO


class PDFRenderer(FPDF):
    def __init__(self, title: str):
        super().__init__()
        self.doc_title = title
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
        # Add basic fonts
        self.set_font("helvetica", size=12)

    def header(self):
        # Arial bold 15
        self.set_font("helvetica", "B", 15)
        # Title
        self.cell(0, 10, self.doc_title, 0, 1, "C")
        # Line break
        self.ln(10)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font("helvetica", "I", 8)
        # Page number
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")


def render_markdown_to_pdf(markdown_text: str, title: str = "Research Document") -> bytes:
    """
    Converts markdown text to a PDF file in-memory using fpdf2's HTML writing feature.
    Returns the raw bytes of the PDF.
    """
    # Convert Markdown to HTML
    html_content = markdown.markdown(markdown_text)

    # Initialize PDF
    pdf = PDFRenderer(title=title)
    
    # fpdf2 supports a subset of HTML tags natively.
    # write_html parses the HTML and applies basic formatting (b, i, u, h1-h6, p, ul, li).
    pdf.write_html(html_content)
    
    # Return PDF bytes
    return bytes(pdf.output())
