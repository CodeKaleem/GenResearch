"use client";

import { useState } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";

// ── Dummy data ────────────────────────────────────────────────
interface UploadedFile {
  id: string;
  name: string;
  size: string;
  pages: number;
  status: "indexed" | "processing" | "failed";
  date: string;
}

const recentUploads: UploadedFile[] = [
  { id: "1", name: "Attention Is All You Need.pdf", size: "2.4 MB", pages: 15, status: "indexed", date: "Today, 2:09 PM" },
  { id: "2", name: "BERT Pre-training of Deep Bidirectional Transformers.pdf", size: "1.8 MB", pages: 13, status: "indexed", date: "Today, 2:09 PM" },
  { id: "3", name: "GPT-4 Technical Report.pdf", size: "5.1 MB", pages: 98, status: "processing", date: "Today, 3:01 PM" },
  { id: "4", name: "Federated Learning Survey 2024.pdf", size: "3.2 MB", pages: 42, status: "indexed", date: "Yesterday" },
  { id: "5", name: "RL_Robotics_Draft.docx", size: "890 KB", pages: 8, status: "failed", date: "2 days ago" },
];

const queueFiles = [
  { name: "Vision_Transformers_2025.pdf", progress: 78, size: "4.2 MB" },
  { name: "Diffusion_Models_Survey.pdf", progress: 45, size: "3.1 MB" },
  { name: "LLM_Safety_Alignment.pdf", progress: 12, size: "2.8 MB" },
];

// ── Status badge ──────────────────────────────────────────────
function StatusBadge({ status }: { status: UploadedFile["status"] }) {
  const map = {
    indexed:    { label: "Indexed",    color: C.green,  bg: "rgba(90,138,60,0.09)" },
    processing: { label: "Processing", color: C.gold,   bg: C.goldFaint },
    failed:     { label: "Failed",     color: C.sienna, bg: "rgba(160,82,45,0.09)" },
  };
  const s = map[status];
  return (
    <span style={{
      padding: "3px 10px", borderRadius: 2,
      background: s.bg, border: `1px solid ${s.color}33`,
      fontFamily: "'Crimson Pro', Georgia, serif",
      fontSize: 11, fontWeight: 600, color: s.color,
      letterSpacing: "0.08em", textTransform: "uppercase",
    }}>{s.label}</span>
  );
}

// ── Main component ────────────────────────────────────────────
export default function UploadPapers() {
  const [dragOver, setDragOver] = useState(false);
  const [hovRow, setHovRow] = useState<string | null>(null);

  return (
    <>
      {/* Page header */}
      <div className="fade-1" style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ height: 1, width: 28, background: C.gold }} />
          <span style={{ ...sectionLabel }}>Document Ingestion</span>
        </div>
        <h1 style={{ ...headingStyle, fontSize: "clamp(24px, 3vw, 34px)" }}>
          Upload <em style={{ color: C.gold }}>Papers</em>
        </h1>
        <p style={{ ...bodyText, fontSize: 15, marginTop: 6, maxWidth: 540 }}>
          Upload research papers for processing. Supported formats: PDF, DOCX, TXT. Maximum file size: 25 MB.
        </p>
      </div>

      {/* Upload zone */}
      <div
        className="fade-2"
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); }}
        style={{
          border: `2px dashed ${dragOver ? C.gold : C.border}`,
          borderRadius: 4,
          padding: "52px 40px",
          textAlign: "center",
          background: dragOver ? C.goldFaint : C.creamLight,
          transition: "all .3s",
          marginBottom: 28,
          cursor: "pointer",
        }}
      >
        <div style={{
          width: 56, height: 56, borderRadius: "50%",
          background: C.goldFaint, border: `1px solid ${C.gold}33`,
          display: "flex", alignItems: "center", justifyContent: "center",
          margin: "0 auto 16px", fontSize: 24,
        }}>↑</div>
        <div style={{
          fontFamily: "'Playfair Display', serif",
          fontSize: 18, fontWeight: 700, color: C.inkDark, marginBottom: 8,
        }}>
          {dragOver ? "Drop files here" : "Drag & drop your research papers"}
        </div>
        <p style={{ ...bodyText, fontSize: 14, marginBottom: 18 }}>
          or click to browse your files
        </p>
        <div style={{ display: "flex", justifyContent: "center", gap: 8 }}>
          {["PDF", "DOCX", "TXT"].map(fmt => (
            <span key={fmt} style={{
              padding: "4px 12px", borderRadius: 2,
              border: `1px solid ${C.border}`,
              fontFamily: "'Crimson Pro', Georgia, serif",
              fontSize: 11, color: C.inkLight,
              letterSpacing: "0.1em",
            }}>{fmt}</span>
          ))}
        </div>
      </div>

      {/* Upload queue */}
      <div className="fade-3" style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
          <div style={{ height: 1, width: 22, background: C.gold }} />
          <span style={{ ...sectionLabel }}>Upload Queue</span>
          <span style={{
            ...sectionLabel,
            color: C.inkLight, fontSize: 11, fontWeight: 400,
          }}>· {queueFiles.length} files</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {queueFiles.map((f, i) => (
            <div key={i} style={{
              ...cardBase,
              padding: "16px 20px",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <div>
                  <div style={{
                    fontFamily: "'Playfair Display', serif",
                    fontSize: 14, fontWeight: 700, color: C.inkDark,
                  }}>{f.name}</div>
                  <span style={{ ...bodyText, fontSize: 12 }}>{f.size}</span>
                </div>
                <span style={{
                  fontFamily: "'Playfair Display', serif",
                  fontSize: 16, fontWeight: 700, color: C.gold,
                }}>{f.progress}%</span>
              </div>
              <div style={{
                height: 4, background: C.creamDark,
                border: `1px solid ${C.border}`, borderRadius: 2, overflow: "hidden",
              }}>
                <div style={{
                  height: "100%", width: `${f.progress}%`,
                  background: `linear-gradient(90deg, ${C.gold}, ${C.goldLight})`,
                  borderRadius: 2, transition: "width 1.2s cubic-bezier(.4,0,.2,1)",
                }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Ornamental divider */}
      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 24 }}>
        <div style={{ flex: 1, height: 1, background: C.border }} />
        <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, color: C.gold }}>✦</div>
        <div style={{ flex: 1, height: 1, background: C.border }} />
      </div>

      {/* Recent uploads table */}
      <div className="fade-4">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ height: 1, width: 22, background: C.gold }} />
            <span style={{ ...sectionLabel }}>Recent Uploads</span>
          </div>
          <span style={{ ...bodyText, fontSize: 12 }}>{recentUploads.length} papers</span>
        </div>

        {/* Table header */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr 80px 60px 100px 120px",
          gap: 12, padding: "10px 20px",
          background: C.creamDark,
          border: `1px solid ${C.border}`,
          borderRadius: "4px 4px 0 0",
        }}>
          {["Paper", "Size", "Pages", "Status", "Uploaded"].map(h => (
            <span key={h} style={{ ...sectionLabel, fontSize: 10 }}>{h}</span>
          ))}
        </div>

        {/* Table rows */}
        {recentUploads.map(f => (
          <div
            key={f.id}
            onMouseEnter={() => setHovRow(f.id)}
            onMouseLeave={() => setHovRow(null)}
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 80px 60px 100px 120px",
              gap: 12, padding: "14px 20px",
              background: hovRow === f.id ? C.white : C.creamLight,
              border: `1px solid ${C.border}`,
              borderTop: "none",
              transition: "all .2s",
              cursor: "pointer",
            }}
          >
            <span style={{
              fontFamily: "'Crimson Pro', Georgia, serif",
              fontSize: 13.5, color: C.inkDark, fontWeight: 500,
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
            }}>{f.name}</span>
            <span style={{ ...bodyText, fontSize: 12.5 }}>{f.size}</span>
            <span style={{ ...bodyText, fontSize: 12.5 }}>{f.pages}</span>
            <StatusBadge status={f.status} />
            <span style={{ ...bodyText, fontSize: 12 }}>{f.date}</span>
          </div>
        ))}
      </div>

      {/* Pro tip */}
      <div className="fade-5" style={{
        marginTop: 28, padding: "20px 24px",
        background: C.inkDark, borderRadius: 4,
        display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap",
      }}>
        <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, fontWeight: 700, color: C.goldLight }}>
          ✦ Tip
        </span>
        <span style={{ ...bodyText, fontSize: 13.5, color: "rgba(245,240,232,0.72)", flex: 1 }}>
          Upload multiple papers on the same topic for better cross-paper analysis. The system indexes content using semantic embeddings for precise RAG retrieval.
        </span>
      </div>
    </>
  );
}
