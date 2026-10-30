"use client";
import { useState, useEffect } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";
import { getCurrentUserId, getUserPapers, type Paper } from "../../lib/db";
import { exportToPDF, exportToDOCX } from "../../lib/exportUtils";

const API = "http://localhost:8000";

function renderInlineMarkdown(text: string, keyPrefix: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*]+\*|_[^_]+_)/g);
  return parts.map((part, index) => {
    if ((part.startsWith("**") && part.endsWith("**")) || (part.startsWith("__") && part.endsWith("__"))) {
      return <strong key={`${keyPrefix}-${index}`}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={`${keyPrefix}-${index}`}>{part.slice(1, -1)}</code>;
    }
    if ((part.startsWith("*") && part.endsWith("*")) || (part.startsWith("_") && part.endsWith("_"))) {
      return <em key={`${keyPrefix}-${index}`}>{part.slice(1, -1)}</em>;
    }
    return part;
  });
}

function FormattedReview({ content }: { content: string }) {
  const lines = content.split(/\r?\n/);
  const blocks: React.ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index].trim();
    if (!line) {
      index++;
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const level = Math.min(heading[1].length, 4);
      const style = level === 1
        ? { fontSize: 24, margin: "8px 0 16px", paddingBottom: 8, borderBottom: `1px solid ${C.borderGold}` }
        : level === 2
          ? { fontSize: 20, margin: "28px 0 10px", paddingBottom: 5, borderBottom: `1px solid ${C.border}` }
          : { fontSize: level === 3 ? 17 : 15, margin: "18px 0 7px" };
      blocks.push(
        <h2
          key={`heading-${index}`}
          style={{ ...headingStyle, ...style, color: level <= 2 ? C.inkDark : C.sienna }}
        >
          {renderInlineMarkdown(heading[2], `heading-${index}`)}
        </h2>
      );
      index++;
      continue;
    }

    const listItem = line.match(/^([-*+]|\d+[.)])\s+(.+)$/);
    if (listItem) {
      const ordered = /^\d/.test(listItem[1]);
      const items: string[] = [];
      while (index < lines.length) {
        const item = lines[index].trim().match(/^([-*+]|\d+[.)])\s+(.+)$/);
        if (!item || /^\d/.test(item[1]) !== ordered) break;
        items.push(item[2]);
        index++;
      }
      const List = ordered ? "ol" : "ul";
      blocks.push(
        <List key={`list-${index}`} style={{ paddingLeft: 26, margin: "8px 0 14px", ...bodyText, color: C.inkDark }}>
          {items.map((item, itemIndex) => (
            <li key={`list-${index}-${itemIndex}`} style={{ paddingLeft: 4, marginBottom: 6 }}>
              {renderInlineMarkdown(item, `list-${index}-${itemIndex}`)}
            </li>
          ))}
        </List>
      );
      continue;
    }

    const paragraph = [line];
    index++;
    while (
      index < lines.length &&
      lines[index].trim() &&
      !/^(#{1,4})\s+|([-*+]|\d+[.)])\s+/.test(lines[index].trim())
    ) {
      paragraph.push(lines[index].trim());
      index++;
    }
    blocks.push(
      <p key={`paragraph-${index}`} style={{ ...bodyText, color: C.inkDark, fontSize: 15, lineHeight: 1.8, marginBottom: 12 }}>
        {renderInlineMarkdown(paragraph.join(" "), `paragraph-${index}`)}
      </p>
    );
  }

  return <div>{blocks}</div>;
}

export default function LiteratureReviewScreen({ onBack }: { onBack: () => void }) {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [focusTopic, setFocusTopic] = useState("");
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
      const res = await fetch(`${API}/agents/literature-review`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, paper_ids: [...selected], focus_topic: focusTopic }),
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
          <div style={{ width: 44, height: 44, borderRadius: 4, background: `${C.sienna}18`, border: `1px solid ${C.sienna}33`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>◉</div>
          <div>
            <h1 style={{ ...headingStyle, fontSize: 28 }}>Literature Review <em style={{ color: C.sienna }}>Agent</em></h1>
            <p style={{ ...bodyText, fontSize: 13, marginTop: 2 }}>Synthesize comparative reviews across multiple papers</p>
          </div>
        </div>
      </div>

      {/* Focus Topic */}
      <div className="fade-2" style={{ ...cardBase, padding: "20px 24px", marginBottom: 16 }}>
        <div style={{ ...sectionLabel, marginBottom: 10 }}>Focus Topic (Optional)</div>
        <input value={focusTopic} onChange={e => setFocusTopic(e.target.value)} placeholder="e.g., Machine learning in education assessment" style={{ width: "100%", padding: "12px 14px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: C.creamLight, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14.5, color: C.inkDark, outline: "none", transition: "border-color .2s" }} onFocus={e => { e.target.style.borderColor = C.sienna; }} onBlur={e => { e.target.style.borderColor = C.border; }} />
        <p style={{ ...bodyText, fontSize: 11.5, marginTop: 6 }}>Leave empty to review all themes, or specify a topic to focus the review.</p>
      </div>

      {/* Paper Selection */}
      <div className="fade-2" style={{ ...cardBase, padding: "24px", marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <div style={{ ...sectionLabel }}>Select Papers ({selected.size} selected)</div>
          <button onClick={() => setSelected(selected.size === papers.length ? new Set() : new Set(papers.map(p => p.id)))} style={{ background: "none", border: "none", cursor: "pointer", ...bodyText, fontSize: 12, color: C.sienna, textDecoration: "underline" }}>
            {selected.size === papers.length ? "Deselect All" : "Select All"}
          </button>
        </div>
        {papers.length === 0 ? (
          <p style={{ ...bodyText, fontSize: 14, textAlign: "center", padding: "20px 0" }}>No indexed papers found.</p>
        ) : papers.map(p => (
          <label key={p.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 14px", marginBottom: 6, background: selected.has(p.id) ? C.siennaFaint : "transparent", border: `1px solid ${selected.has(p.id) ? "rgba(160,82,45,0.3)" : C.border}`, borderRadius: 4, cursor: "pointer", transition: "all .2s" }}>
            <input type="checkbox" checked={selected.has(p.id)} onChange={() => toggle(p.id)} style={{ accentColor: C.sienna, width: 16, height: 16 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, fontWeight: 700, color: C.inkDark }}>{p.title}</div>
              <div style={{ ...bodyText, fontSize: 11.5 }}>{p.authors || "Unknown"} · {p.chunks} chunks</div>
            </div>
          </label>
        ))}
      </div>

      <div className="fade-3" style={{ marginBottom: 32 }}>
        <button onClick={run} disabled={loading || selected.size === 0} style={{ width: "100%", padding: "14px 0", background: loading || selected.size === 0 ? C.creamDark : C.inkDark, color: loading || selected.size === 0 ? C.inkLight : C.cream, border: "none", borderRadius: 4, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", cursor: loading || selected.size === 0 ? "not-allowed" : "pointer", transition: "all .3s" }}>
          {loading ? "⟳ Generating Literature Review..." : `Generate Review from ${selected.size} Paper${selected.size !== 1 ? "s" : ""}`}
        </button>
      </div>

      {result && !result.error && (
        <div className="fade-1">
          <div style={{ ...cardBase, padding: "28px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, fontWeight: 700, color: C.inkDark }}>Literature Review</div>
                {result.focus_topic && <div style={{ ...bodyText, fontSize: 12, color: C.sienna }}>Focus: {result.focus_topic}</div>}
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 10 }}>
                <div style={{ ...bodyText, fontSize: 11, color: C.gold }}>{result.papers_analyzed} papers · {result.chunks_used} excerpts</div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button onClick={() => exportToPDF("Literature_Review", result.review)} style={{ padding: "4px 8px", background: "transparent", color: C.sienna, border: `1px solid ${C.sienna}`, borderRadius: 3, cursor: "pointer", fontSize: 11 }}>PDF</button>
                  <button onClick={() => exportToDOCX("Literature_Review", result.review)} style={{ padding: "4px 8px", background: "transparent", color: C.inkDark, border: `1px solid ${C.inkDark}`, borderRadius: 3, cursor: "pointer", fontSize: 11 }}>DOCX</button>
                </div>
              </div>
            </div>
            <div style={{ padding: "4px 8px" }}>
              <FormattedReview content={result.review} />
            </div>
          </div>
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
