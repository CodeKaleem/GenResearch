"use client";

import { useState, useEffect } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";
import { getCurrentUserId, subscribeToResults, type TaskResult as DBResult } from "../../lib/db";
import type { DiscoverySearchPayload } from "../../lib/db";

import { exportToPDF, exportToDOCX } from "../../lib/exportUtils";

type ResultType = "summary" | "review" | "citation" | "proposal" | "case_studies" | "research_papers";
interface Result {
  id: string; title: string; agent: string; type: ResultType;
  score: number; date: string; preview: string;
  discovery?: DiscoverySearchPayload;
}

const typeConfig: Record<ResultType, { label: string; agent: string; color: string }> = {
  summary:  { label: "Summary",  agent: "Summarization Agent",  color: C.gold },
  review:   { label: "Review",   agent: "Literature Review Agent",   color: C.sienna },
  citation: { label: "Citation", agent: "Citation Agent", color: C.umber },
  proposal: { label: "Proposal", agent: "Proposal Drafting Agent", color: C.inkMid },
  case_studies: { label: "Case Studies", agent: "Case Study Search", color: C.sienna },
  research_papers: { label: "Paper Search", agent: "Academic Discovery", color: C.blue },
};

function parseDiscoveryContent(content: string): DiscoverySearchPayload | null {
  try {
    const parsed = JSON.parse(content) as DiscoverySearchPayload;
    return parsed.kind === "discovery_search" ? parsed : null;
  } catch {
    return null;
  }
}

function mapStoredResults(dbResults: DBResult[]): Result[] {
  const standardResults: Result[] = [];
  const discoveryGroups = new Map<string, { row: DBResult; payload: DiscoverySearchPayload }>();

  for (const row of dbResults) {
    const payload = parseDiscoveryContent(row.content);
    if (!payload) {
      const type = row.type as ResultType;
      standardResults.push({
        id: row.id,
        title: row.title,
        agent: typeConfig[type]?.agent || "Unknown Agent",
        type,
        score: row.score,
        date: new Date(row.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
        preview: row.content,
      });
      continue;
    }

    const groupId = row.task_id || row.id;
    const existing = discoveryGroups.get(groupId);
    if (!existing) {
      discoveryGroups.set(groupId, { row, payload });
      continue;
    }

    discoveryGroups.set(groupId, {
      row: existing.row,
      payload: {
        ...existing.payload,
        records: existing.payload.records.length ? existing.payload.records : payload.records,
        reports: {
          all: existing.payload.reports.all || payload.reports.all,
          byStudy: { ...payload.reports.byStudy, ...existing.payload.reports.byStudy },
        },
      },
    });
  }

  const discoveryResults = [...discoveryGroups.entries()].map(([id, group]) => {
    const type = group.payload.category;
    const preview = group.payload.reports.all || group.payload.query;
    return {
      id,
      title: group.row.title,
      agent: typeConfig[type].agent,
      type,
      score: group.row.score,
      date: new Date(group.row.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
      preview,
      discovery: group.payload,
    };
  });

  return [...standardResults, ...discoveryResults].sort((left, right) =>
    new Date(right.date).getTime() - new Date(left.date).getTime()
  );
}

function getResultText(result: Result): string {
  if (!result.discovery) return result.preview;
  const discovery = result.discovery;
  const entries = discovery.records.map((record, index) => {
    const authors = Array.isArray(record.authors) ? record.authors.join(", ") : record.authors || "Unknown authors";
    const metadata = [authors, record.year || "n.d.", record.venue, record.source].filter(Boolean).join(" · ");
    return `## ${index + 1}. ${record.title || "Untitled"}\n${metadata}\n\n${record.abstract || "Abstract unavailable."}${record.url ? `\n\n${record.url}` : ""}`;
  });
  const summaries = Object.entries(discovery.reports.byStudy).map(([key, text]) => `## Summary: ${key}\n\n${text}`);
  return [
    `# ${discovery.category === "case_studies" ? "Case Study Search" : "Research Paper Search"}`,
    `Query: ${discovery.query}`,
    discovery.reports.all,
    ...summaries,
    `## ${discovery.category === "case_studies" ? "Case Studies" : "Research Papers"}`,
    ...entries,
  ].filter(Boolean).join("\n\n");
}

function ResultCard({ result, expanded, onToggle }: { result: Result; expanded: boolean; onToggle: () => void }) {
  const [hov, setHov] = useState(false);
  const tc = typeConfig[result.type] || typeConfig.summary;
  const resultText = getResultText(result);

  const handleShare = (e: React.MouseEvent) => {
    e.stopPropagation();
    const shareText = `GenResearch Output: ${result.title}\nAgent: ${result.agent}\n\n${resultText.substring(0, 300)}...`;
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
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexShrink: 0, flexWrap: "wrap", justifyContent: "flex-end" }}>
          <span style={{ padding: "3px 10px", borderRadius: 2, background: `${tc.color}15`, border: `1px solid ${tc.color}33`, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: tc.color, letterSpacing: "0.08em", textTransform: "uppercase" }}>{tc.label}</span>
          {result.discovery && <button className="btn-outline" onClick={(event) => { event.stopPropagation(); onToggle(); }}>{expanded ? "Hide search results" : "View search results"}</button>}
          {!result.discovery && <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 16, fontWeight: 700, color: C.gold }}>{result.score}</span>
            <span style={{ ...bodyText, fontSize: 11 }}>/100</span>
          </div>}
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: 14, paddingTop: 14, borderTop: `1px solid ${C.border}` }}>
          {result.discovery && <p style={{ ...bodyText, marginBottom: 14 }}>Search query: <strong style={{ color: C.inkDark }}>{result.discovery.query}</strong></p>}
          {result.discovery?.reports.all && <><div style={{ ...sectionLabel, fontSize: 10, marginBottom: 10 }}>Generated Report</div><div style={{ ...bodyText, fontSize: 13.5, lineHeight: 1.7, whiteSpace: "pre-wrap", background: C.creamDark, padding: "16px 18px", borderRadius: 3, border: `1px solid ${C.border}`, marginBottom: 18 }}>{result.discovery.reports.all}</div></>}
          {result.discovery && Object.entries(result.discovery.reports.byStudy).map(([key, summary]) => (
            <div key={key} style={{ marginBottom: 18 }}><div style={{ ...sectionLabel, fontSize: 10, marginBottom: 10 }}>Paper Summary · {key}</div><div style={{ ...bodyText, fontSize: 13.5, lineHeight: 1.7, whiteSpace: "pre-wrap", background: C.creamDark, padding: "16px 18px", borderRadius: 3, border: `1px solid ${C.border}` }}>{summary}</div></div>
          ))}
          {result.discovery && <div style={{ ...sectionLabel, fontSize: 10, margin: "18px 0 10px" }}>{result.discovery.category === "case_studies" ? "Case Studies" : "Research Papers"} · {result.discovery.records.length}</div>}
          {result.discovery?.records.map((record, index) => {
            const authors = Array.isArray(record.authors) ? record.authors.join(", ") : record.authors || "Unknown authors";
            return <article key={`${record.title}-${index}`} style={{ padding: "12px 0", borderTop: `1px solid ${C.border}` }}>
              <strong style={{ color: C.inkDark }}>{index + 1}. {record.title || "Untitled"}</strong>
              <p style={{ ...bodyText, fontSize: 12 }}>{[authors, record.year || "n.d.", record.venue, record.source].filter(Boolean).join(" · ")}</p>
              {record.abstract && <p style={{ ...bodyText, color: C.inkDark, fontSize: 13, marginTop: 5 }}>{record.abstract}</p>}
              {record.url && <a href={record.url} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()} style={{ display: "inline-block", color: C.blue, fontSize: 12, marginTop: 6 }}>Open source</a>}
            </article>;
          })}
          {!result.discovery && <><div style={{ ...sectionLabel, fontSize: 10, marginBottom: 10 }}>Output Preview</div><div style={{ ...bodyText, fontSize: 13.5, lineHeight: 1.7, whiteSpace: "pre-wrap", background: C.creamDark, padding: "16px 18px", borderRadius: 3, border: `1px solid ${C.border}` }}>{result.preview}</div></>}
          <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
            <button className="btn-gold" style={{ padding: "7px 14px", fontSize: 11 }} onClick={(e) => { e.stopPropagation(); exportToPDF(result.title, resultText); }}>↓ PDF</button>
            <button className="btn-ink" style={{ padding: "7px 14px", fontSize: 11 }} onClick={(e) => { e.stopPropagation(); void exportToDOCX(result.title, resultText); }}>↓ DOCX</button>
            <button className="btn-outline" style={{ padding: "7px 14px", fontSize: 11 }} onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(resultText).catch(() => {}); alert("Copied to clipboard!"); }}>Copy Text</button>
            <button className="btn-outline" style={{ padding: "7px 14px", fontSize: 11 }} onClick={handleShare}>🔗 Share</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Results({ focusedTaskId = null }: { focusedTaskId?: string | null }) {
  const [dbResults, setDbResults] = useState<DBResult[]>([]);
  const [activeFilter, setActiveFilter] = useState<ResultType | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(focusedTaskId);

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

  const results = mapStoredResults(dbResults);

  const filters: { key: ResultType | "all"; label: string }[] = [
    { key: "all", label: "All" }, { key: "summary", label: "Summaries" },
    { key: "review", label: "Reviews" }, { key: "citation", label: "Citations" },
    { key: "proposal", label: "Proposals" },
    { key: "case_studies", label: "Case Studies" },
    { key: "research_papers", label: "Paper Searches" },
  ];

  const filtered = results.filter(r => {
    const matchesFilter = activeFilter === "all" || r.type === activeFilter;
    const q = searchQuery.toLowerCase().trim();
    const matchesSearch = !q || r.title.toLowerCase().includes(q) || r.preview.toLowerCase().includes(q) || r.agent.toLowerCase().includes(q);
    return matchesFilter && matchesSearch;
  });

  const exportAllFiltered = () => {
    if (filtered.length === 0) return alert("No results to export.");
    const combinedText = filtered.map(r => `# ${r.title}\nAgent: ${r.agent} (${r.date})\n\n${getResultText(r)}\n\n---\n`).join("\n");
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
