"use client";
import { useState, useEffect } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";
import { getCurrentUserId, getUserPapers, type Paper } from "../../lib/db";
import { exportToPDF, exportToDOCX } from "../../lib/exportUtils";

const API = "http://localhost:8000";
const STYLES = [
  { key: "apa", label: "APA 7th Edition", desc: "Author-Date style, most common in social sciences" },
  { key: "mla", label: "MLA 9th Edition", desc: "Used in humanities and liberal arts" },
  { key: "ieee", label: "IEEE", desc: "Numbered style, used in engineering and CS" },
  { key: "chicago", label: "Chicago 17th", desc: "Notes-Bibliography, used in history and arts" },
];

export default function CitationScreen({ onBack }: { onBack: () => void }) {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [style, setStyle] = useState("apa");
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
    setSelected(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; });
  };

  const run = async () => {
    if (!userId || selected.size === 0) return;
    setLoading(true); setResult(null);
    try {
      const res = await fetch(`${API}/agents/citations`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, paper_ids: [...selected], style }),
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      setResult(await res.json());
    } catch (e: any) { setResult({ error: e.message }); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      <div className="fade-1" style={{ marginBottom: 28 }}>
        <button onClick={onBack} style={{ background: "none", border: "none", cursor: "pointer", ...bodyText, fontSize: 13, color: C.gold, marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>← Back to Agents</button>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ width: 44, height: 44, borderRadius: 4, background: `${C.umber}18`, border: `1px solid ${C.umber}33`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>◎</div>
          <div>
            <h1 style={{ ...headingStyle, fontSize: 28 }}>Citation <em style={{ color: C.umber }}>Agent</em></h1>
            <p style={{ ...bodyText, fontSize: 13, marginTop: 2 }}>Extract and format references in multiple citation styles</p>
          </div>
        </div>
      </div>

      {/* Citation Style Picker */}
      <div className="fade-2" style={{ ...cardBase, padding: "20px 24px", marginBottom: 16 }}>
        <div style={{ ...sectionLabel, marginBottom: 12 }}>Citation Style</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {STYLES.map(s => (
            <button key={s.key} onClick={() => setStyle(s.key)} style={{ padding: "12px 16px", textAlign: "left", background: style === s.key ? C.goldFaint : "transparent", border: `1.5px solid ${style === s.key ? C.borderGold : C.border}`, borderRadius: 4, cursor: "pointer", transition: "all .2s" }}>
              <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, fontWeight: 700, color: style === s.key ? C.gold : C.inkDark }}>{s.label}</div>
              <div style={{ ...bodyText, fontSize: 11.5 }}>{s.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Paper Selection */}
      <div className="fade-2" style={{ ...cardBase, padding: "24px", marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <div style={{ ...sectionLabel }}>Select Papers ({selected.size})</div>
          <button onClick={() => setSelected(selected.size === papers.length ? new Set() : new Set(papers.map(p => p.id)))} style={{ background: "none", border: "none", cursor: "pointer", ...bodyText, fontSize: 12, color: C.gold, textDecoration: "underline" }}>
            {selected.size === papers.length ? "Deselect All" : "Select All"}
          </button>
        </div>
        {papers.length === 0 ? (
          <p style={{ ...bodyText, fontSize: 14, textAlign: "center", padding: "20px 0" }}>No indexed papers found.</p>
        ) : papers.map(p => (
          <label key={p.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 14px", marginBottom: 6, background: selected.has(p.id) ? C.goldFaint : "transparent", border: `1px solid ${selected.has(p.id) ? C.borderGold : C.border}`, borderRadius: 4, cursor: "pointer", transition: "all .2s" }}>
            <input type="checkbox" checked={selected.has(p.id)} onChange={() => toggle(p.id)} style={{ accentColor: C.gold, width: 16, height: 16 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, fontWeight: 700, color: C.inkDark }}>{p.title}</div>
              <div style={{ ...bodyText, fontSize: 11.5 }}>{p.authors || "Unknown"} · {p.chunks} chunks</div>
            </div>
          </label>
        ))}
      </div>

      <div className="fade-3" style={{ marginBottom: 32 }}>
        <button onClick={run} disabled={loading || selected.size === 0} style={{ width: "100%", padding: "14px 0", background: loading || selected.size === 0 ? C.creamDark : C.inkDark, color: loading || selected.size === 0 ? C.inkLight : C.cream, border: "none", borderRadius: 4, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", cursor: loading || selected.size === 0 ? "not-allowed" : "pointer", transition: "all .3s" }}>
          {loading ? "⟳ Extracting Citations..." : `Extract Citations (${style.toUpperCase()})`}
        </button>
      </div>

      {result && !result.error && result.results?.map((r: any, i: number) => (
        <div key={i} className="fade-1" style={{ ...cardBase, padding: "24px", marginBottom: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 16, fontWeight: 700, color: C.inkDark }}>{r.title}</div>
              <span style={{ ...sectionLabel, fontSize: 10, background: C.goldFaint, padding: "3px 10px", borderRadius: 12 }}>{r.style}</span>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => exportToPDF(`Citations_${r.title}`, r.citations_text)} style={{ padding: "4px 8px", background: "transparent", color: C.umber, border: `1px solid ${C.umber}`, borderRadius: 3, cursor: "pointer", fontSize: 11 }}>PDF</button>
              <button onClick={() => exportToDOCX(`Citations_${r.title}`, r.citations_text)} style={{ padding: "4px 8px", background: "transparent", color: C.inkDark, border: `1px solid ${C.inkDark}`, borderRadius: 3, cursor: "pointer", fontSize: 11 }}>DOCX</button>
            </div>
          </div>
          <div style={{ ...bodyText, fontSize: 14, lineHeight: 1.8, whiteSpace: "pre-wrap" }}>{r.citations_text}</div>
        </div>
      ))}

      {result?.error && (
        <div style={{ ...cardBase, padding: "20px", borderColor: "rgba(160,82,45,0.3)", background: "rgba(160,82,45,0.05)" }}>
          <span style={{ ...bodyText, color: C.sienna }}>⚠ {result.error}</span>
        </div>
      )}
    </div>
  );
}
