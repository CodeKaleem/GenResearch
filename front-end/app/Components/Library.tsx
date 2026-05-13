"use client";

import { useState } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";

interface Collection { id: string; name: string; count: number; color: string; icon: string; }
interface LibPaper { id: string; title: string; authors: string; year: number; collection: string; pages: number; date: string; }

const collections: Collection[] = [
  { id: "all", name: "All Papers", count: 12, color: C.gold, icon: "⊞" },
  { id: "nlp", name: "NLP & Transformers", count: 5, color: C.sienna, icon: "◈" },
  { id: "cv", name: "Computer Vision", count: 2, color: C.umber, icon: "◉" },
  { id: "rl", name: "Reinforcement Learning", count: 2, color: C.green, icon: "◎" },
  { id: "fl", name: "Federated Learning", count: 1, color: C.inkMid, icon: "◐" },
  { id: "gen", name: "Generative Models", count: 2, color: C.goldLight, icon: "✦" },
];

const libPapers: LibPaper[] = [
  { id: "1", title: "Attention Is All You Need", authors: "Vaswani et al.", year: 2017, collection: "nlp", pages: 15, date: "May 4" },
  { id: "2", title: "BERT: Pre-training of Deep Bidirectional Transformers", authors: "Devlin et al.", year: 2019, collection: "nlp", pages: 13, date: "May 4" },
  { id: "3", title: "GPT-4 Technical Report", authors: "OpenAI", year: 2023, collection: "nlp", pages: 98, date: "May 4" },
  { id: "4", title: "Chain-of-Thought Prompting Elicits Reasoning", authors: "Wei et al.", year: 2022, collection: "nlp", pages: 18, date: "Apr 29" },
  { id: "5", title: "LoRA: Low-Rank Adaptation of LLMs", authors: "Hu et al.", year: 2022, collection: "nlp", pages: 17, date: "Apr 28" },
  { id: "6", title: "Vision Transformers for Dense Prediction", authors: "Ranftl et al.", year: 2021, collection: "cv", pages: 22, date: "Apr 26" },
  { id: "7", title: "Deep Residual Learning for Image Recognition", authors: "He et al.", year: 2016, collection: "cv", pages: 12, date: "Apr 24" },
  { id: "8", title: "Reinforcement Learning in Robotics", authors: "Kober et al.", year: 2023, collection: "rl", pages: 38, date: "May 1" },
  { id: "9", title: "Proximal Policy Optimization Algorithms", authors: "Schulman et al.", year: 2017, collection: "rl", pages: 12, date: "Apr 20" },
  { id: "10", title: "A Survey on Federated Learning", authors: "Li et al.", year: 2024, collection: "fl", pages: 42, date: "May 3" },
  { id: "11", title: "Diffusion Models: A Comprehensive Survey", authors: "Yang et al.", year: 2024, collection: "gen", pages: 55, date: "Apr 30" },
  { id: "12", title: "LLaMA: Open Foundation Language Models", authors: "Touvron et al.", year: 2023, collection: "gen", pages: 27, date: "Apr 27" },
];

export default function Library() {
  const [activeColl, setActiveColl] = useState("all");
  const [hovRow, setHovRow] = useState<string | null>(null);
  const filtered = activeColl === "all" ? libPapers : libPapers.filter(p => p.collection === activeColl);

  return (
    <>
      <div className="fade-1" style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ height: 1, width: 28, background: C.gold }} />
          <span style={{ ...sectionLabel }}>Knowledge Repository</span>
        </div>
        <h1 style={{ ...headingStyle, fontSize: "clamp(24px, 3vw, 34px)" }}>Research <em style={{ color: C.gold }}>Library</em></h1>
        <p style={{ ...bodyText, fontSize: 15, marginTop: 6 }}>Organize your papers into collections for focused analysis.</p>
      </div>

      {/* Collections grid */}
      <div className="fade-2" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: 12, marginBottom: 28 }}>
        {collections.map(col => {
          const active = activeColl === col.id;
          return (
            <button key={col.id} onClick={() => setActiveColl(col.id)} style={{ ...cardBase, padding: "18px 16px", textAlign: "left", cursor: "pointer", background: active ? C.white : C.creamLight, borderColor: active ? C.borderGold : C.border, transform: active ? "translateY(-2px)" : "none", boxShadow: active ? `0 6px 20px ${C.shadow}` : "none" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ fontSize: 18, color: col.color }}>{col.icon}</span>
                <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, fontWeight: 900, color: active ? col.color : C.inkDark }}>{col.count}</span>
              </div>
              <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, fontWeight: active ? 600 : 400, color: active ? C.inkDark : C.inkLight }}>{col.name}</div>
            </button>
          );
        })}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 24 }}>
        <div style={{ flex: 1, height: 1, background: C.border }} />
        <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, color: C.gold }}>✦</div>
        <div style={{ flex: 1, height: 1, background: C.border }} />
      </div>

      {/* Table */}
      <div className="fade-3">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 150px 60px 60px 80px", gap: 12, padding: "10px 20px", background: C.creamDark, border: `1px solid ${C.border}`, borderRadius: "4px 4px 0 0" }}>
          {["Title", "Authors", "Year", "Pages", "Added"].map(h => <span key={h} style={{ ...sectionLabel, fontSize: 10 }}>{h}</span>)}
        </div>
        {filtered.map((p, i) => (
          <div key={p.id} onMouseEnter={() => setHovRow(p.id)} onMouseLeave={() => setHovRow(null)} style={{ display: "grid", gridTemplateColumns: "1fr 150px 60px 60px 80px", gap: 12, padding: "13px 20px", background: hovRow === p.id ? C.white : C.creamLight, border: `1px solid ${C.border}`, borderTop: "none", transition: "all .2s", cursor: "pointer", animation: `fadeUp .4s ${i * 0.04 + 0.1}s both` }}>
            <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkDark, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.title}</span>
            <span style={{ ...bodyText, fontSize: 12.5 }}>{p.authors}</span>
            <span style={{ ...bodyText, fontSize: 12.5 }}>{p.year}</span>
            <span style={{ ...bodyText, fontSize: 12.5 }}>{p.pages}</span>
            <span style={{ ...bodyText, fontSize: 12 }}>{p.date}</span>
          </div>
        ))}
      </div>

      {/* Storage summary */}
      <div className="fade-4" style={{ ...cardBase, padding: "22px 24px", marginTop: 28 }}>
        <div style={{ ...sectionLabel, fontSize: 10, marginBottom: 14 }}>Storage Usage</div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
          <span style={{ ...bodyText, fontSize: 13 }}>1.2 GB of 5 GB used</span>
          <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 15, fontWeight: 700, color: C.gold }}>24%</span>
        </div>
        <div style={{ height: 6, background: C.creamDark, border: `1px solid ${C.border}`, borderRadius: 3, overflow: "hidden" }}>
          <div style={{ height: "100%", width: "24%", background: `linear-gradient(90deg, ${C.gold}, ${C.goldLight})`, borderRadius: 3 }} />
        </div>
      </div>
    </>
  );
}
