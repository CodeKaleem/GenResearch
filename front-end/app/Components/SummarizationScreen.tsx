"use client";
import { useState, useEffect } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";
import { getCurrentUserId, getUserPapers, type Paper } from "../../lib/db";
import { exportToPDF, exportToDOCX } from "../../lib/exportUtils";

const API = "http://localhost:8000";

export default function SummarizationScreen({ onBack }: { onBack: () => void }) {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    getCurrentUserId().then(uid => {
      setUserId(uid);
      if (uid) getUserPapers(uid).then(({ data }) => setPapers(data.filter(p => p.status === "indexed")));
    });
  }, []);

  const toggle = (id: string) => {
    setSelected(prev => {
      const s = new Set(prev);
      s.has(id) ? s.delete(id) : s.add(id);
      return s;
    });
  };

  const run = async () => {
    if (!userId || selected.size === 0) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${API}/agents/summarize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, paper_ids: [...selected] }),
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      setResult(await res.json());
    } catch (e: any) {
      setResult({ error: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      {/* Header */}
      <div className="fade-1" style={{ marginBottom: 28 }}>
        <button onClick={onBack} style={{ background: "none", border: "none", cursor: "pointer", ...bodyText, fontSize: 13, color: C.gold, marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
          ← Back to Agents
        </button>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ width: 44, height: 44, borderRadius: 4, background: `${C.gold}18`, border: `1px solid ${C.gold}33`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>◈</div>
          <div>
            <h1 style={{ ...headingStyle, fontSize: 28 }}>Summarization <em style={{ color: C.gold }}>Agent</em></h1>
            <p style={{ ...bodyText, fontSize: 13, marginTop: 2 }}>Generate structured summaries of your research papers</p>
          </div>
        </div>
      </div>

      {/* Paper Selection */}
      <div className="fade-2" style={{ ...cardBase, padding: "24px", marginBottom: 24 }}>
        <div style={{ ...sectionLabel, marginBottom: 14 }}>Select Papers to Summarize</div>
        {papers.length === 0 ? (
          <p style={{ ...bodyText, fontSize: 14, textAlign: "center", padding: "20px 0" }}>No indexed papers found. Upload papers first.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <span style={{ ...bodyText, fontSize: 12 }}>{selected.size} of {papers.length} selected</span>
              <button onClick={() => setSelected(selected.size === papers.length ? new Set() : new Set(papers.map(p => p.id)))} style={{ background: "none", border: "none", cursor: "pointer", ...bodyText, fontSize: 12, color: C.gold, textDecoration: "underline" }}>
                {selected.size === papers.length ? "Deselect All" : "Select All"}
              </button>
            </div>
            {papers.map(p => (
              <label key={p.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 14px", background: selected.has(p.id) ? C.goldFaint : "transparent", border: `1px solid ${selected.has(p.id) ? C.borderGold : C.border}`, borderRadius: 4, cursor: "pointer", transition: "all .2s" }}>
                <input type="checkbox" checked={selected.has(p.id)} onChange={() => toggle(p.id)} style={{ accentColor: C.gold, width: 16, height: 16 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, fontWeight: 700, color: C.inkDark }}>{p.title}</div>
                  <div style={{ ...bodyText, fontSize: 11.5 }}>{p.authors || "Unknown author"} · {p.chunks} chunks · {p.file_size}</div>
                </div>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Run Button */}
      <div className="fade-3" style={{ marginBottom: 32 }}>
        <button onClick={run} disabled={loading || selected.size === 0} style={{ width: "100%", padding: "14px 0", background: loading || selected.size === 0 ? C.creamDark : C.inkDark, color: loading || selected.size === 0 ? C.inkLight : C.cream, border: "none", borderRadius: 4, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", cursor: loading || selected.size === 0 ? "not-allowed" : "pointer", transition: "all .3s" }}>
          {loading ? "⟳ Generating Summaries..." : `Summarize ${selected.size} Paper${selected.size !== 1 ? "s" : ""}`}
        </button>
      </div>

      {/* Results */}
      {result && !result.error && (
        <div className="fade-1">
          <div style={{ ...sectionLabel, marginBottom: 14 }}>Generated Summaries</div>
          {result.summaries?.map((s: any, i: number) => (
            <div key={i} style={{ ...cardBase, padding: "24px", marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
                <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 16, fontWeight: 700, color: C.inkDark }}>{s.title}</div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button onClick={() => exportToPDF(`Summary_${s.title}`, s.summary)} style={{ padding: "4px 8px", background: "transparent", color: C.gold, border: `1px solid ${C.gold}`, borderRadius: 3, cursor: "pointer", fontSize: 11 }}>PDF</button>
                  <button onClick={() => exportToDOCX(`Summary_${s.title}`, s.summary)} style={{ padding: "4px 8px", background: "transparent", color: C.inkDark, border: `1px solid ${C.inkDark}`, borderRadius: 3, cursor: "pointer", fontSize: 11 }}>DOCX</button>
                </div>
              </div>
              <div style={{ ...bodyText, fontSize: 11, marginBottom: 14, color: C.gold }}>{s.chunks_used || 0} chunks analyzed · Status: {s.status}</div>
              <div style={{ ...bodyText, fontSize: 14, lineHeight: 1.8, whiteSpace: "pre-wrap" }}>{s.summary}</div>
            </div>
          ))}
        </div>
      )}

      {result?.error && (
        <div style={{ ...cardBase, padding: "20px", borderColor: "rgba(160,82,45,0.3)", background: "rgba(160,82,45,0.05)" }}>
          <span style={{ ...bodyText, color: C.sienna }}>⚠ {result.error}</span>
        </div>
      )}
    </div>
  );
}
