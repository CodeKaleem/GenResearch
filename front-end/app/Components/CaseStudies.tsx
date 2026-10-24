"use client";

import { useState } from "react";
import { C, bodyText, cardBase, headingStyle, sectionLabel } from "./theme";
import { exportToDOCX, exportToPDF } from "../../lib/exportUtils";
import {
  getCurrentUserId,
  appendDiscoverySearchResult,
  saveDiscoverySearchResult,
  type DiscoverySearchPayload,
} from "../../lib/db";

interface CaseStudy {
  title: string;
  authors: string;
  year: number | null;
  venue: string;
  abstract: string;
  doi: string;
  url: string;
  source: string;
  keywords: string[];
  candidate: boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function CaseStudies() {
  const [topic, setTopic] = useState("");
  const [limit, setLimit] = useState(10);
  const [results, setResults] = useState<CaseStudy[]>([]);
  const [report, setReport] = useState("");
  const [reportTitle, setReportTitle] = useState("General report of all studies");
  const [reportingStudy, setReportingStudy] = useState("");
  const [savedSearch, setSavedSearch] = useState<{ taskId: string; title: string; payload: DiscoverySearchPayload } | null>(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);

  const search = async () => {
    const searchTopic = topic.trim();
    if (searchTopic.length < 3) {
      setStatus("Enter a topic or short description of at least 3 characters.");
      return;
    }

    setLoading(true);
    setResults([]);
    setReport("");
    setSavedSearch(null);
    setStatus("Searching academic and web sources...");
    try {
      const response = await fetch(`${API_BASE}/search-case-studies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: searchTopic, limit }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Case-study search failed.");
      const studies: CaseStudy[] = data.case_studies || [];
      setResults(studies);
      setStatus(studies.length ? "" : "No case-study candidates were found. Try a broader description.");
      const payload: DiscoverySearchPayload = {
        kind: "discovery_search",
        category: "case_studies",
        query: data.query || searchTopic,
        records: studies,
        reports: { all: "", byStudy: {} },
      };
      const userId = await getCurrentUserId();
      if (userId) {
        try {
          const saved = await saveDiscoverySearchResult(
            userId,
            `Case Studies: ${searchTopic}`,
            payload,
          );
          setSavedSearch({ taskId: saved.task_id, title: `Case Studies: ${searchTopic}`, payload });
        } catch {
          setStatus("Search finished, but could not save it to Results.");
        }
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Search failed. Check that the API is running.");
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async (studies: CaseStudy[], reportType: "single" | "all") => {
    if (studies.length === 0) return;
    setReportingStudy(reportType === "single" ? studies[0].title : "all");
    setReport("");
    setReportTitle(reportType === "single" ? `Summary: ${studies[0].title}` : "General report of all studies");
    setReportLoading(true);
    setStatus(reportType === "single" ? "Summarizing the selected study..." : "Generating a report of all studies...");
    try {
      const response = await fetch(`${API_BASE}/generate-case-study-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic.trim(), studies, report_type: reportType }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Report generation failed.");
      setReport(data.report || "");
      setReportTitle(reportType === "single" ? `Summary: ${studies[0].title}` : "General report of all studies");
      if (savedSearch) {
        const reports = reportType === "single"
          ? {
              ...savedSearch.payload.reports,
              byStudy: {
                ...savedSearch.payload.reports.byStudy,
                [studies[0].doi || studies[0].url || studies[0].title]: data.report || "",
              },
            }
          : { ...savedSearch.payload.reports, all: data.report || "" };
        const payload = { ...savedSearch.payload, reports };
        try {
          const userId = await getCurrentUserId();
          if (userId) {
            await appendDiscoverySearchResult(
              userId,
              savedSearch.taskId,
              savedSearch.title,
              { ...payload, records: [] },
            );
          }
          setSavedSearch({ ...savedSearch, payload });
        } catch {
          setStatus("Report generated, but could not update the saved Results entry.");
        }
      }
      setStatus(data.report ? "" : "The report came back empty. Try generating again.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Report generation failed.");
    } finally {
      setReportLoading(false);
      setReportingStudy("");
    }
  };

  return (
    <div style={{ maxWidth: 1040, margin: "0 auto" }}>
      <header className="fade-1" style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <span style={{ width: 28, height: 1, background: C.sienna }} />
          <span style={{ ...sectionLabel, color: C.sienna }}>Field Evidence</span>
        </div>
        <h1 style={{ ...headingStyle, fontSize: 34 }}>Case studies</h1>
        <p style={{ ...bodyText, maxWidth: 650, fontSize: 16, marginTop: 8 }}>
          Find documented real-world examples by topic or research description.
        </p>
      </header>

      <section className="fade-2" style={{ ...cardBase, padding: 24, marginBottom: 30 }}>
        <label htmlFor="case-study-topic" style={{ display: "block" }}>
          <span style={{ ...sectionLabel, display: "block", marginBottom: 9 }}>Topic or short description</span>
          <textarea
            id="case-study-topic"
            value={topic}
            onChange={(event) => setTopic(event.target.value.slice(0, 1200))}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void search();
              }
            }}
            placeholder="e.g. Smallholder farms adopting solar-powered irrigation in drought-prone regions"
            maxLength={1200}
            rows={3}
            style={{
              width: "100%", resize: "vertical", minHeight: 82, padding: "12px 14px",
              border: `1px solid ${C.borderGold}`, borderRadius: 3, background: C.white,
              color: C.inkDark, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 16,
              lineHeight: 1.5, outlineColor: C.gold,
            }}
          />
        </label>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap", borderTop: `1px solid ${C.border}`, marginTop: 18, paddingTop: 16 }}>
          <label style={{ ...bodyText, display: "flex", alignItems: "center", gap: 10, fontSize: 14 }}>
            Maximum results
            <select
              value={limit}
              onChange={(event) => setLimit(Number(event.target.value))}
              style={{ border: `1px solid ${C.borderGold}`, borderRadius: 3, padding: "7px 28px 7px 9px", background: C.creamLight, color: C.inkDark, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14 }}
            >
              {[5, 10, 15, 20].map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <button type="button" className="btn-gold" onClick={() => void search()} disabled={loading} style={{ minWidth: 210, opacity: loading ? 0.7 : 1 }}>
            {loading ? "Searching sources…" : "Search case studies"}
          </button>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginTop: 12 }}>
          {status && <p role="status" style={{ ...bodyText, color: status.startsWith("No ") || status.startsWith("Enter") || status.includes("failed") ? C.sienna : C.gold, fontSize: 13 }}>{status}</p>}
          <span style={{ ...bodyText, marginLeft: "auto", fontSize: 12 }}>{topic.length}/1200</span>
        </div>
      </section>

      {loading && (
        <div role="status" aria-live="polite" style={{ display: "flex", alignItems: "center", gap: 12, padding: "20px 0", color: C.inkLight }}>
          <span aria-hidden="true" style={{ width: 18, height: 18, border: `2px solid ${C.borderGold}`, borderTopColor: C.sienna, borderRadius: "50%", animation: "spin 1s linear infinite" }} />
          Searching across configured scholarly sources…
        </div>
      )}

      {results.length > 0 && (
        <section aria-live="polite">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", borderBottom: `1.5px solid ${C.inkDark}`, paddingBottom: 10, marginBottom: 4 }}>
            <h2 style={{ ...headingStyle, fontSize: 23 }}>Search results</h2>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ ...bodyText, fontSize: 13 }}>{results.length} candidates</span>
              <button type="button" className="btn-ink" onClick={() => void generateReport(results, "all")} disabled={reportLoading} style={{ opacity: reportLoading ? 0.7 : 1 }}>
                {reportingStudy === "all" ? "Generating report…" : reportTitle === "General report of all studies" && report ? "Regenerate all-study report" : "Generate report for all studies"}
              </button>
            </div>
          </div>
          {results.map((study, index) => (
            <article key={`${study.source}-${study.title}-${index}`} style={{ display: "grid", gridTemplateColumns: "42px minmax(0, 1fr)", gap: 14, padding: "21px 0", borderBottom: `1px solid ${C.border}` }}>
              <span aria-hidden="true" style={{ color: C.sienna, fontFamily: "'Playfair Display', serif", fontWeight: 700, fontSize: 15, paddingTop: 2 }}>{String(index + 1).padStart(2, "0")}</span>
              <div style={{ minWidth: 0 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "flex-start", flexWrap: "wrap", marginBottom: 6 }}>
                  <h3 style={{ flex: "1 1 360px", color: C.inkDark, fontFamily: "'Playfair Display', serif", fontSize: 18, lineHeight: 1.35 }}>{study.title}</h3>
                  <span style={{ color: C.sienna, border: `1px solid ${C.sienna}55`, background: C.siennaFaint, padding: "3px 8px", fontSize: 11, fontWeight: 600, textTransform: "uppercase" }}>Candidate</span>
                </div>
                <p style={{ ...bodyText, fontSize: 13, marginBottom: 9 }}>
                  {[study.authors, study.venue, study.year || "Year unavailable"].filter(Boolean).join(" · ")}
                </p>
                <p style={{ color: C.inkDark, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 15, lineHeight: 1.6, whiteSpace: "pre-line", overflowWrap: "anywhere" }}>{study.abstract}</p>
                {study.keywords.length > 0 && (
                  <p style={{ ...bodyText, fontSize: 12, marginTop: 8 }}>Keywords: {study.keywords.join(", ")}</p>
                )}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center", marginTop: 11, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12 }}>
                  <span style={{ color: C.inkLight }}>{study.source}</span>
                  {study.doi && <a href={`https://doi.org/${study.doi.replace(/^https?:\/\/doi\.org\//i, "")}`} target="_blank" rel="noreferrer" style={{ color: C.blue, textDecoration: "underline", overflowWrap: "anywhere" }}>DOI: {study.doi.replace(/^https?:\/\/doi\.org\//i, "")}</a>}
                  {study.url && <a href={study.url} target="_blank" rel="noreferrer" style={{ color: C.blue, textDecoration: "underline", overflowWrap: "anywhere" }}>Open source</a>}
                  <button type="button" className="btn-outline" onClick={() => void generateReport([study], "single")} disabled={reportLoading}>
                    {reportingStudy === study.title ? "Summarizing…" : "Summarize this paper"}
                  </button>
                </div>
              </div>
            </article>
          ))}
        </section>
      )}

      {reportLoading && (
        <p role="status" aria-live="polite" style={{ ...bodyText, color: C.gold, marginTop: 22 }}>
          Synthesizing the available abstracts and checking each statement against its source…
        </p>
      )}

      {report && (
        <section aria-live="polite" style={{ marginTop: 32 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 14, flexWrap: "wrap", borderBottom: `1.5px solid ${C.inkDark}`, paddingBottom: 10, marginBottom: 16 }}>
            <h2 style={{ ...headingStyle, fontSize: 23 }}>{reportTitle}</h2>
            <div style={{ display: "flex", gap: 8 }}>
              <button type="button" className="btn-gold" onClick={() => exportToPDF("Case_Study_Report", report)}>↓ PDF</button>
              <button type="button" className="btn-ink" onClick={() => void exportToDOCX("Case_Study_Report", report)}>↓ Word</button>
            </div>
          </div>
          <article style={{ ...cardBase, padding: "24px clamp(18px, 4vw, 42px)", color: C.inkDark, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 16, lineHeight: 1.75, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
            {report}
          </article>
          <p style={{ ...bodyText, fontSize: 12, marginTop: 10 }}>
            Report statements are based on the returned abstracts; open the source records above to verify full-text details.
          </p>
        </section>
      )}
    </div>
  );
}