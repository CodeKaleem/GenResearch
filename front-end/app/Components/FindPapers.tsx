"use client";

import { useState } from "react";
import { C, bodyText, cardBase, headingStyle, sectionLabel } from "./theme";

type SearchMode = "topic" | "document";

interface PaperResult {
  title: string;
  authors: string;
  venue: string;
  year: number | string | null;
  abstract: string;
  citations: number;
  url: string;
  source: string;
}

const API_BASE = "http://localhost:8000";

export default function FindPapers() {
  const [mode, setMode] = useState<SearchMode>("topic");
  const [topic, setTopic] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [count, setCount] = useState(5);
  const [results, setResults] = useState<PaperResult[]>([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (mode === "topic" && !topic.trim()) {
      setStatus("Enter a research topic to begin.");
      return;
    }
    if (mode === "document" && !file) {
      setStatus("Choose a PDF to search from.");
      return;
    }

    const form = new FormData();
    form.append("mode", mode);
    form.append("num_papers", String(count));
    if (mode === "topic") form.append("topic", topic.trim());
    if (file) form.append("document", file);

    setLoading(true);
    setStatus("Searching academic sources...");
    try {
      const response = await fetch(`${API_BASE}/search-papers`, { method: "POST", body: form });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Search failed.");
      setResults(data.papers || []);
      setStatus(data.papers?.length ? "" : "No papers were found for this search.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Search failed. Check that the API is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="fade-1" style={{ marginBottom: 30 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 7 }}>
          <div style={{ height: 1, width: 28, background: C.gold }} />
          <span style={sectionLabel}>Academic Discovery</span>
        </div>
        <h1 style={{ ...headingStyle, fontSize: "clamp(24px, 3vw, 34px)" }}>Find research <em style={{ color: C.gold }}>papers</em></h1>
        <p style={{ ...bodyText, fontSize: 15, maxWidth: 600, marginTop: 7 }}>
          Search trusted academic indexes by topic, or use an existing paper to discover related work.
        </p>
      </div>

      <div className="fade-2" style={{ ...cardBase, padding: 24, maxWidth: 820, marginBottom: 30 }}>
        <div style={{ display: "flex", gap: 8, borderBottom: `1px solid ${C.border}`, marginBottom: 24 }} role="tablist" aria-label="Paper search mode">
          {(["topic", "document"] as SearchMode[]).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => { setMode(item); setStatus(""); }}
              aria-pressed={mode === item}
              style={{
                border: "none", borderBottom: `2px solid ${mode === item ? C.gold : "transparent"}`,
                background: "transparent", color: mode === item ? C.inkDark : C.inkLight,
                padding: "0 4px 12px", marginRight: 18, cursor: "pointer",
                fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 15, fontWeight: mode === item ? 600 : 400,
              }}
            >{item === "topic" ? "Search by topic" : "Search from a PDF"}</button>
          ))}
        </div>

        {mode === "topic" ? (
          <label style={{ display: "block" }}>
            <span style={{ ...sectionLabel, display: "block", marginBottom: 8 }}>Research topic</span>
            <input
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              onKeyDown={(event) => { if (event.key === "Enter") search(); }}
              placeholder="e.g. transformer models for low-resource languages"
              style={{ width: "100%", border: "none", borderBottom: `1.5px solid ${C.inkDark}`, background: "transparent", padding: "10px 2px", color: C.inkDark, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 18, outline: "none" }}
            />
          </label>
        ) : (
          <label
            htmlFor="paper-discovery-file"
            style={{ display: "block", padding: "25px 18px", border: `1.5px dashed ${C.borderGold}`, borderRadius: 4, textAlign: "center", cursor: "pointer", background: C.goldFaint }}
          >
            <input id="paper-discovery-file" type="file" accept="application/pdf" hidden onChange={(event) => setFile(event.target.files?.[0] || null)} />
            <strong style={{ display: "block", color: C.inkDark, fontFamily: "'Playfair Display', serif", fontSize: 16, marginBottom: 5 }}>{file ? file.name : "Choose a research PDF"}</strong>
            <span style={{ ...bodyText, fontSize: 13 }}>{file ? "Ready to extract a search topic" : "PDF files only · the document title and text will guide the search"}</span>
          </label>
        )}

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap", borderTop: `1px solid ${C.border}`, marginTop: 24, paddingTop: 18 }}>
          <label style={{ ...bodyText, fontSize: 14, display: "flex", alignItems: "center", gap: 9 }}>
            Papers to return
            <select value={count} onChange={(event) => setCount(Number(event.target.value))} style={{ border: `1px solid ${C.borderGold}`, borderRadius: 3, padding: "7px 28px 7px 9px", background: C.creamLight, color: C.inkDark, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14 }}>
              {[3, 5, 10, 15, 20].map(value => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <button type="button" className="btn-gold" onClick={search} disabled={loading} style={{ minWidth: 170 }}>
            {loading ? "Searching..." : "Find papers"}
          </button>
        </div>
        {status && <p role="status" style={{ ...bodyText, color: status.includes("failed") || status.includes("Enter") || status.includes("Choose") ? C.sienna : C.gold, fontSize: 13, marginTop: 14 }}>{status}</p>}
      </div>

      {results.length > 0 && (
        <section className="fade-2" style={{ maxWidth: 820 }} aria-live="polite">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", borderBottom: `1.5px solid ${C.inkDark}`, paddingBottom: 10, marginBottom: 2 }}>
            <h2 style={{ ...headingStyle, fontSize: 22 }}>Search results</h2>
            <span style={{ ...bodyText, fontSize: 13 }}>{results.length} papers</span>
          </div>
          {results.map((paper, index) => (
            <article key={`${paper.title}-${index}`} style={{ display: "grid", gridTemplateColumns: "38px 1fr", gap: 14, padding: "20px 0", borderBottom: `1px solid ${C.border}` }}>
              <span style={{ color: C.gold, fontFamily: "'Playfair Display', serif", fontWeight: 700, fontSize: 16 }}>{String(index + 1).padStart(2, "0")}</span>
              <div>
                <h3 style={{ color: C.inkDark, fontFamily: "'Playfair Display', serif", fontSize: 17, lineHeight: 1.3, marginBottom: 6 }}>{paper.title}</h3>
                <p style={{ ...bodyText, fontSize: 13, marginBottom: 8 }}>{paper.authors} · {paper.venue} · {paper.year || "n.d."}</p>
                <p style={{ ...bodyText, color: C.inkDark, fontSize: 14, lineHeight: 1.55, marginBottom: 10 }}>{paper.abstract}</p>
                <div style={{ display: "flex", gap: 14, alignItems: "center", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12 }}>
                  <span style={{ border: `1px solid ${C.border}`, padding: "3px 8px", color: C.inkLight }}>{paper.citations} citations</span>
                  {paper.url && <a href={paper.url} target="_blank" rel="noreferrer" style={{ color: C.blue, borderBottom: `1px solid ${C.blue}`, textDecoration: "none" }}>View source</a>}
                </div>
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}