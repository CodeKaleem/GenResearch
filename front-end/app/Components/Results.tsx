"use client";

import { useState } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";

type ResultType = "summary" | "review" | "citation" | "proposal";
interface Result {
  id: string; title: string; agent: string; type: ResultType;
  score: number; date: string; preview: string;
}

const results: Result[] = [
  { id: "1", title: "Transformer Architectures in NLP", agent: "Summarization Agent", type: "summary", score: 87, date: "Today, 2:14 PM", preview: "This paper introduces the Transformer architecture, which relies entirely on self-attention mechanisms. Key contributions include multi-head attention, positional encoding, and the encoder-decoder framework that has become the foundation for modern NLP…" },
  { id: "2", title: "Federated Learning Survey — Key Findings", agent: "Summarization Agent", type: "summary", score: 92, date: "Yesterday", preview: "A comprehensive overview of federated learning paradigms. The survey categorizes FL into horizontal, vertical, and transfer approaches. Key challenges identified include communication efficiency, data heterogeneity, and privacy guarantees…" },
  { id: "3", title: "BERT vs GPT Comparative Analysis", agent: "Literature Review Agent", type: "review", score: 88, date: "Today, 3:01 PM", preview: "Comparative analysis reveals fundamental architectural differences: BERT employs bidirectional encoding while GPT uses autoregressive decoding. Performance benchmarks show BERT excels in classification tasks while GPT demonstrates superior generation…" },
  { id: "4", title: "Reinforcement Learning in Robotics — Proposal", agent: "Proposal Drafting Agent", type: "proposal", score: 79, date: "3 days ago", preview: "Research Proposal: Investigating the application of model-based reinforcement learning to robotic manipulation tasks. Proposed methodology includes sim-to-real transfer using domain randomization and curriculum learning strategies…" },
  { id: "5", title: "Computer Vision Benchmarks — References", agent: "Citation Agent", type: "citation", score: 95, date: "2 days ago", preview: "[1] He, K., Zhang, X., Ren, S., & Sun, J. (2016). Deep Residual Learning for Image Recognition. CVPR.\n[2] Dosovitskiy, A. et al. (2021). An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale. ICLR." },
];

const typeConfig: Record<ResultType, { label: string; color: string }> = {
  summary:  { label: "Summary",  color: C.gold },
  review:   { label: "Review",   color: C.sienna },
  citation: { label: "Citation", color: C.umber },
  proposal: { label: "Proposal", color: C.inkMid },
};

function ResultCard({ result, expanded, onToggle }: { result: Result; expanded: boolean; onToggle: () => void }) {
  const [hov, setHov] = useState(false);
  const tc = typeConfig[result.type];
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
          <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
            <button className="btn-ink" style={{ padding: "7px 16px", fontSize: 11 }} onClick={(e) => { e.stopPropagation(); alert("Download started for: " + result.title); }}>Download</button>
            <button className="btn-outline" style={{ padding: "7px 16px", fontSize: 11 }} onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(result.preview).catch(() => {}); alert("Copied to clipboard!"); }}>Copy</button>
            <button className="btn-outline" style={{ padding: "7px 16px", fontSize: 11 }} onClick={(e) => { e.stopPropagation(); alert("Re-running task: " + result.title); }}>Re-run</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Results() {
  const [activeFilter, setActiveFilter] = useState<ResultType | "all">("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const filters: { key: ResultType | "all"; label: string }[] = [
    { key: "all", label: "All" }, { key: "summary", label: "Summaries" },
    { key: "review", label: "Reviews" }, { key: "citation", label: "Citations" },
    { key: "proposal", label: "Proposals" },
  ];
  const filtered = results.filter(r => activeFilter === "all" || r.type === activeFilter);

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
          <button className="btn-gold" style={{ padding: "8px 18px", fontSize: 11.5 }} onClick={() => alert("Exporting all " + results.length + " results…")}>Export All</button>
        </div>
      </div>

      <div className="fade-2" style={{ display: "flex", gap: 6, marginBottom: 24, flexWrap: "wrap" }}>
        {filters.map(f => (
          <button key={f.key} onClick={() => setActiveFilter(f.key)} style={{ padding: "6px 16px", borderRadius: 2, cursor: "pointer", border: `1px solid ${activeFilter === f.key ? C.gold : C.border}`, background: activeFilter === f.key ? C.goldFaint : "transparent", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, fontWeight: activeFilter === f.key ? 600 : 400, color: activeFilter === f.key ? C.gold : C.inkLight, transition: "all .2s" }}>{f.label}</button>
        ))}
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
      {filtered.length === 0 && <div style={{ textAlign: "center", padding: "60px 20px", ...bodyText, fontSize: 15 }}>No results match the selected filter.</div>}
    </>
  );
}
