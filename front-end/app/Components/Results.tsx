"use client";

import { useState, useEffect } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";
import { getCurrentUserId, subscribeToResults, type TaskResult as DBResult } from "../../lib/db";

import { exportToPDF, exportToDOCX } from "../../lib/exportUtils";

type ResultType = "summary" | "review" | "citation" | "proposal";
interface Result {
  id: string; title: string; agent: string; type: ResultType;
  score: number; date: string; preview: string;
}

const typeConfig: Record<ResultType, { label: string; agent: string; color: string }> = {
  summary:  { label: "Summary",  agent: "Summarization Agent",  color: C.gold },
  review:   { label: "Review",   agent: "Literature Review Agent",   color: C.sienna },
  citation: { label: "Citation", agent: "Citation Agent", color: C.umber },
  proposal: { label: "Proposal", agent: "Proposal Drafting Agent", color: C.inkMid },
};

function ResultCard({ result, expanded, onToggle }: { result: Result; expanded: boolean; onToggle: () => void }) {
  const [hov, setHov] = useState(false);
  const tc = typeConfig[result.type] || typeConfig.summary;

  const handleShare = (e: React.MouseEvent) => {
    e.stopPropagation();
    const shareText = `📚 GenResearch Output: ${result.title}\nAgent: ${result.agent}\nScore: ${result.score}/100\n\n${result.preview.substring(0, 300)}...`;
    navigator.clipboard.writeText(shareText).catch(() => {});
    alert("Shareable summary copied to clipboard!");
  };

  return (
    <div onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)} style={{ ...cardBase, padding: "22px 24px", background: hov || expanded ? C.white : C.creamLight, borderColor: hov || expanded ? C.borderGold : C.border, transition: "all .25s", cursor: "pointer" }} onClick={onToggle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div style={{ flex: 1, paddingRight: 12 }}>
          <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 16, fontWeight: 700, color: C.inkDark, marginBottom: 4, lineHeight: 1.3 }}>{result.title}</div>
          <div style={{ ...bodyText, fontSize: 12 }}>{result.agent} · {result.date}</div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexShrink: 0 }}>
          <span style={{ padding: "3px 10px", borderRadius: 2, background: `${tc.color}15`, border: `1px solid ${tc.color}33`, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: tc.color, letterSpacing: "0.08em", textTransform: "uppercase" }}>{tc.label}</span>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 16, fontWeight: 700, color: C.gold }}>{result.score}</span>
            <span style={{ ...bodyText, fontSize: 11 }}>/100</span>
          </div>
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: 14, paddingTop: 14, borderTop: `1px solid ${C.border}` }}>
          <div style={{ ...sectionLabel, fontSize: 10, marginBottom: 10 }}>Output Preview</div>
          <div style={{ ...bodyText, fontSize: 13.5, lineHeight: 1.7, whiteSpace: "pre-wrap", background: C.creamDark, padding: "16px 18px", borderRadius: 3, border: `1px solid ${C.border}` }}>{result.preview}</div>
          <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
            <button className="btn-gold" style={{ padding: "7px 14px", fontSize: 11 }} onClick={(e) => { e.stopPropagation(); exportToPDF(result.title, result.preview); }}>↓ PDF</button>
            <button className="btn-ink" style={{ padding: "7px 14px", fontSize: 11 }} onClick={(e) => { e.stopPropagation(); exportToDOCX(result.title, result.preview); }}>↓ DOCX</button>
            <button className="btn-outline" style={{ padding: "7px 14px", fontSize: 11 }} onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(result.preview).catch(() => {}); alert("Copied to clipboard!"); }}>Copy Text</button>
            <button className="btn-outline" style={{ padding: "7px 14px", fontSize: 11 }} onClick={handleShare}>🔗 Share</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Results() {
  const [dbResults, setDbResults] = useState<DBResult[]>([]);
  const [activeFilter, setActiveFilter] = useState<ResultType | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    let unsub: (() => void) | undefined;
    getCurrentUserId().then(uid => {
      if (uid && isMounted) unsub = subscribeToResults(uid, setDbResults);
    });
    return () => {
      isMounted = false;
      unsub?.();
    };
  }, []);

  const results: Result[] = dbResults.map(r => ({
    id: r.id,
    title: r.title,
    agent: typeConfig[r.type as ResultType]?.agent || "Unknown Agent",
    type: r.type as ResultType,
    score: r.score,
    date: new Date(r.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
    preview: r.content
  }));

  const filters: { key: ResultType | "all"; label: string }[] = [
    { key: "all", label: "All" }, { key: "summary", label: "Summaries" },
    { key: "review", label: "Reviews" }, { key: "citation", label: "Citations" },
    { key: "proposal", label: "Proposals" },
  ];

  const filtered = results.filter(r => {
    const matchesFilter = activeFilter === "all" || r.type === activeFilter;
    const q = searchQuery.toLowerCase().trim();
    const matchesSearch = !q || r.title.toLowerCase().includes(q) || r.preview.toLowerCase().includes(q) || r.agent.toLowerCase().includes(q);
    return matchesFilter && matchesSearch;
  });

  const exportAllFiltered = () => {
    if (filtered.length === 0) return alert("No results to export.");
    const combinedText = filtered.map(r => `# ${r.title}\nAgent: ${r.agent} (${r.date})\nScore: ${r.score}/100\n\n${r.preview}\n\n---\n`).join("\n");
    exportToPDF("All_Research_Results", combinedText);
  };

  return (
    <>
      <div className="fade-1" style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ height: 1, width: 28, background: C.gold }} />
          <span style={{ ...sectionLabel }}>Research Output</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1 style={{ ...headingStyle, fontSize: "clamp(24px, 3vw, 34px)" }}>Task <em style={{ color: C.gold }}>Results</em></h1>
            <p style={{ ...bodyText, fontSize: 14, marginTop: 4 }}>{results.length} completed outputs ready to review</p>
          </div>
          <button onClick={exportAllFiltered} className="btn-gold" style={{ padding: "8px 18px", fontSize: 11.5 }}>Export All ({filtered.length})</button>
        </div>
      </div>

      <div className="fade-2" style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ position: "relative", flex: 1, minWidth: 220 }}>
          <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: C.inkLight, fontSize: 13 }}>🔍</span>
          <input
            placeholder="Search within results & content..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ width: "100%", padding: "9px 14px 9px 34px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: C.white, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkDark, outline: "none" }}
            onFocus={e => (e.target.style.borderColor = C.gold)}
            onBlur={e => (e.target.style.borderColor = C.border)}
          />
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {filters.map(f => (
            <button key={f.key} onClick={() => setActiveFilter(f.key)} style={{ padding: "6px 16px", borderRadius: 2, cursor: "pointer", border: `1px solid ${activeFilter === f.key ? C.gold : C.border}`, background: activeFilter === f.key ? C.goldFaint : "transparent", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, fontWeight: activeFilter === f.key ? 600 : 400, color: activeFilter === f.key ? C.gold : C.inkLight, transition: "all .2s" }}>{f.label}</button>
          ))}
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 24 }}>
        <div style={{ flex: 1, height: 1, background: C.border }} />
        <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, color: C.gold }}>✦</div>
        <div style={{ flex: 1, height: 1, background: C.border }} />
      </div>

      <div className="fade-3" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {filtered.map((r, i) => (
          <div key={r.id} style={{ animation: `fadeUp .5s ${i * 0.06 + 0.1}s both` }}>
            <ResultCard result={r} expanded={expandedId === r.id} onToggle={() => setExpandedId(expandedId === r.id ? null : r.id)} />
          </div>
        ))}
      </div>
      {filtered.length === 0 && <div style={{ textAlign: "center", padding: "60px 20px", ...bodyText, fontSize: 15 }}>No results match your search and filter criteria.</div>}
    </>
  );
}
