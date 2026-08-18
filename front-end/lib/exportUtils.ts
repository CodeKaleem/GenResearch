import { jsPDF } from "jspdf";
import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType } from "docx";

/**
 * Enhanced PDF export with page numbers, headers, footers, and academic formatting.
 */
export function exportToPDF(title: string, text: string) {
  const doc = new jsPDF();
  const pageHeight = doc.internal.pageSize.height;
  const pageWidth = doc.internal.pageSize.width;
  const margin = 20;
  const maxLineWidth = pageWidth - (margin * 2);

  // Header
  doc.setFont("times", "bold");
  doc.setFontSize(18);
  doc.text(title, margin, margin + 5);

  doc.setLineWidth(0.5);
  doc.setDrawColor(139, 105, 20);
  doc.line(margin, margin + 9, pageWidth - margin, margin + 9);

  // Body
  doc.setFont("times", "normal");
  doc.setFontSize(11);

  const lines = text.split("\n");
  let y = margin + 20;

  const checkAddPage = (neededSpace = 10) => {
    if (y + neededSpace > pageHeight - margin) {
      doc.addPage();
      y = margin + 10;
    }
  };

  for (const line of lines) {
    if (line.startsWith("### ")) {
      checkAddPage(12);
      doc.setFont("times", "bold");
      doc.setFontSize(13);
      doc.text(line.replace("### ", ""), margin, y);
      y += 8;
      doc.setFont("times", "normal");
      doc.setFontSize(11);
    } else if (line.startsWith("## ")) {
      checkAddPage(14);
      doc.setFont("times", "bold");
      doc.setFontSize(15);
      doc.text(line.replace("## ", ""), margin, y);
      y += 10;
      doc.setFont("times", "normal");
      doc.setFontSize(11);
    } else if (line.startsWith("# ")) {
      checkAddPage(16);
      doc.setFont("times", "bold");
      doc.setFontSize(17);
      doc.text(line.replace("# ", ""), margin, y);
      y += 12;
      doc.setFont("times", "normal");
      doc.setFontSize(11);
    } else if (line.trim().length > 0) {
      const splitText = doc.splitTextToSize(line, maxLineWidth);
      checkAddPage(splitText.length * 5);
      doc.text(splitText, margin, y);
      y += (splitText.length * 5.5);
    } else {
      y += 4;
    }
  }

  // Footer / Page numbers
  const totalPages = (doc as any).internal.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFont("times", "italic");
    doc.setFontSize(9);
    doc.setTextColor(120, 100, 80);
    doc.text(`GenResearch Academic System  |  Page ${i} of ${totalPages}`, pageWidth / 2, pageHeight - 10, { align: "center" });
  }

  doc.save(`${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.pdf`);
}

/**
 * Enhanced DOCX export with professional academic typography and heading styles.
 */
export async function exportToDOCX(title: string, text: string) {
  const lines = text.split("\n");
  const children: any[] = [];

  // Title Header
  children.push(
    new Paragraph({
      text: title,
      heading: HeadingLevel.HEADING_1,
      alignment: AlignmentType.CENTER,
      spacing: { after: 300 },
    })
  );

  for (const line of lines) {
    if (line.startsWith("### ")) {
      children.push(
        new Paragraph({
          text: line.replace("### ", ""),
          heading: HeadingLevel.HEADING_3,
          spacing: { before: 200, after: 100 },
        })
      );
    } else if (line.startsWith("## ")) {
      children.push(
        new Paragraph({
          text: line.replace("## ", ""),
          heading: HeadingLevel.HEADING_2,
          spacing: { before: 300, after: 150 },
        })
      );
    } else if (line.startsWith("# ")) {
      children.push(
        new Paragraph({
          text: line.replace("# ", ""),
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 400, after: 200 },
        })
      );
    } else if (line.trim().length > 0) {
      children.push(
        new Paragraph({
          children: [new TextRun({ text: line, font: "Georgia", size: 23 })],
          spacing: { line: 276, after: 120 }, // 1.15 line spacing
        })
      );
    } else {
      children.push(new Paragraph({ text: "", spacing: { after: 100 } }));
    }
  }

  const doc = new Document({
    sections: [{
      properties: {},
      children: children,
    }]
  });

  const blob = await Packer.toBlob(doc);
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.docx`;
  a.click();
  window.URL.revokeObjectURL(url);
}
