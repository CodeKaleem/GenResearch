"use client";

import { useState, useEffect } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";
import { getCurrentUserId, subscribeToPapers, createPaper, type Paper as DBPaper } from "../../lib/db";

// ── Types ───────────────────────────────────────────────────
interface UploadedFile {
  id: string;
  name: string;
  size: string;
  pages: number;
  status: "indexed" | "processing" | "unread" | "failed";
  date: string;
}

// ── Status badge ──────────────────────────────────────────────
function StatusBadge({ status }: { status: UploadedFile["status"] }) {
  const map = {
    indexed:    { label: "Indexed",    color: C.green,  bg: "rgba(90,138,60,0.09)" },
    processing: { label: "Processing", color: C.gold,   bg: C.goldFaint },
    unread:     { label: "Unread",     color: C.umber,  bg: "rgba(139,69,19,0.09)" },
    failed:     { label: "Failed",     color: C.sienna, bg: "rgba(160,82,45,0.09)" },
  };
  const s = map[status] || map.unread;
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
  const [dbPapers, setDbPapers] = useState<DBPaper[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [hovRow, setHovRow] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMode, setUploadMode] = useState<"single" | "batch">("single");
  const [error, setError] = useState("");

  useEffect(() => {
    let unsub: (() => void) | undefined;
    getCurrentUserId().then(uid => {
      if (uid) unsub = subscribeToPapers(uid, setDbPapers);
    });
    return () => unsub?.();
  }, []);

  const recentUploads: UploadedFile[] = dbPapers.slice(0, 8).map(p => ({
    id: p.id,
    name: p.file_name || p.title,
    size: p.file_size,
    pages: p.pages,
    status: p.status,
    date: new Date(p.created_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
  }));

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const uid = await getCurrentUserId();
    if (!uid) {
      setError("User session not found. Please login again.");
      return;
    }

    setUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("user_id", uid);
      formData.append("collection", "Library"); // Default collection
      
      let endpoint = "http://localhost:8000/papers/upload";
      
      if (uploadMode === "single" || files.length === 1) {
        formData.append("file", files[0]);
        formData.append("title", files[0].name.split(".")[0]);
      } else {
        endpoint = "http://localhost:8000/papers/upload-batch";
        for (let i = 0; i < files.length; i++) {
          formData.append("files", files[i]);
        }
      }

      const response = await fetch(endpoint, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Upload failed");
      }

      // Success! The database subscription will pick up the new records
      console.log("Upload successful");
    } catch (err: any) {
      console.error("Upload error:", err);
      setError(err.message || "An error occurred during upload.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      <div className="fade-1" style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <div style={{ height: 1, width: 28, background: C.gold }} />
              <span style={{ ...sectionLabel }}>Document Ingestion</span>
            </div>
            <h1 style={{ ...headingStyle, fontSize: "clamp(24px, 3vw, 34px)" }}>
              Upload <em style={{ color: C.gold }}>Papers</em>
            </h1>
            <p style={{ ...bodyText, fontSize: 15, marginTop: 6, maxWidth: 540 }}>
              Upload research papers for processing. Supported format: PDF. Maximum file size: 25 MB.
            </p>
          </div>
          <div style={{ padding: "12px 18px", background: C.creamDark, border: `1px solid ${C.border}`, borderRadius: 4, textAlign: "right" }}>
            <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 700, color: C.gold, textTransform: "uppercase", letterSpacing: "0.1em" }}>Account Quota</div>
            <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, fontWeight: 800, color: dbPapers.length >= 20 ? C.sienna : C.inkDark, marginTop: 2 }}>
              {dbPapers.length} / 20 <span style={{ fontSize: 12, fontWeight: 400, color: C.inkLight }}>Papers</span>
            </div>
          </div>
        </div>
      </div>

      <div className="fade-2" style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        <button 
          onClick={() => setUploadMode("single")}
          style={{ 
            flex: 1, padding: "16px", borderRadius: 4, 
            background: uploadMode === "single" ? C.white : "transparent",
            border: `1.5px solid ${uploadMode === "single" ? C.gold : C.border}`,
            color: uploadMode === "single" ? C.inkDark : C.inkLight,
            fontFamily: "'Playfair Display', serif", fontWeight: 700, fontSize: 15,
            cursor: "pointer", transition: "all .2s"
          }}
        >
          <span style={{ display: "block", fontSize: 11, ...sectionLabel, color: uploadMode === "single" ? C.gold : C.inkLight, marginBottom: 4 }}>Option 01</span>
          Single Paper
        </button>
        <button 
          onClick={() => setUploadMode("batch")}
          style={{ 
            flex: 1, padding: "16px", borderRadius: 4, 
            background: uploadMode === "batch" ? C.white : "transparent",
            border: `1.5px solid ${uploadMode === "batch" ? C.gold : C.border}`,
            color: uploadMode === "batch" ? C.inkDark : C.inkLight,
            fontFamily: "'Playfair Display', serif", fontWeight: 700, fontSize: 15,
            cursor: "pointer", transition: "all .2s"
          }}
        >
          <span style={{ display: "block", fontSize: 11, ...sectionLabel, color: uploadMode === "batch" ? C.gold : C.inkLight, marginBottom: 4 }}>Option 02</span>
          Batch Upload
        </button>
      </div>

      {error && (
        <div className="fade-in" style={{ padding: "12px 20px", background: "rgba(160,82,45,0.08)", border: `1px solid ${C.sienna}33`, borderRadius: 4, color: C.sienna, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, marginBottom: 20, display: "flex", alignItems: "center", gap: 10 }}>
          <span>⚠️</span> {error}
        </div>
      )}

      <div
        className="fade-3"
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFileUpload(e.dataTransfer.files); }}
        onClick={() => document.getElementById("file-input")?.click()}
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
        <input 
          id="file-input" 
          type="file" 
          multiple={uploadMode === "batch"} 
          accept=".pdf"
          style={{ display: "none" }} 
          onChange={(e) => handleFileUpload(e.target.files)} 
        />
        <div style={{
          width: 56, height: 56, borderRadius: "50%",
          background: C.goldFaint, border: `1px solid ${C.gold}33`,
          display: "flex", alignItems: "center", justifyContent: "center",
          margin: "0 auto 16px", fontSize: 24,
        }}>{uploading ? "⌛" : "↑"}</div>
        <div style={{
          fontFamily: "'Playfair Display', serif",
          fontSize: 18, fontWeight: 700, color: C.inkDark, marginBottom: 8,
        }}>
          {uploading 
            ? `Processing ${uploadMode === "batch" ? "Batch" : "Paper"}...` 
            : dragOver 
              ? "Drop PDF here" 
              : `Drag & drop ${uploadMode === "batch" ? "multiple PDFs" : "a single PDF"}`}
        </div>
        <p style={{ ...bodyText, fontSize: 14, marginBottom: 18 }}>
          or click to browse your {uploadMode === "batch" ? "folder" : "files"}
        </p>
        <div style={{ display: "flex", justifyContent: "center", gap: 8 }}>
          <span style={{
            padding: "4px 12px", borderRadius: 2,
            border: `1px solid ${C.gold}66`,
            background: C.goldFaint,
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 11, color: C.gold,
            letterSpacing: "0.1em", fontWeight: 600
          }}>PDF ONLY</span>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 24 }}>
        <div style={{ flex: 1, height: 1, background: C.border }} />
        <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, color: C.gold }}>✦</div>
        <div style={{ flex: 1, height: 1, background: C.border }} />
      </div>

      <div className="fade-4">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ height: 1, width: 22, background: C.gold }} />
            <span style={{ ...sectionLabel }}>Recent Uploads</span>
          </div>
          <span style={{ ...bodyText, fontSize: 12 }}>{recentUploads.length} papers</span>
        </div>

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

        {recentUploads.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 0", ...cardBase, borderTop: "none" }}>No uploads yet.</div>
        ) : (
          recentUploads.map(f => (
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
          ))
        )}
      </div>

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
