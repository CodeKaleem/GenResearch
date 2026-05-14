"use client";

import { useState, useEffect } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";
import { getCurrentUserId, subscribeToPapers, type Paper as DBPaper } from "../../lib/db";

interface Collection { id: string; name: string; count: number; color: string; icon: string; }
interface LibPaper { id: string; title: string; authors: string; year: number; collection: string; pages: number; date: string; size: string; }

export default function Library() {
  const [dbPapers, setDbPapers] = useState<DBPaper[]>([]);
  const [activeColl, setActiveColl] = useState("all");
  const [hovRow, setHovRow] = useState<string | null>(null);

  useEffect(() => {
    let unsub: (() => void) | undefined;
    getCurrentUserId().then(uid => {
      if (uid) unsub = subscribeToPapers(uid, setDbPapers);
    });
    return () => unsub?.();
  }, []);

  const papers: LibPaper[] = dbPapers.map(p => ({
    id: p.id,
    title: p.title,
    authors: p.authors.split(",")[0] + (p.authors.includes(",") ? " et al." : ""),
    year: p.year || 0,
    collection: p.collection?.toLowerCase() || "uncategorized",
    pages: p.pages,
    date: new Date(p.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    size: p.file_size || "0 KB"
  }));

  // Dynamically build collections
  const uniqueCollections = Array.from(new Set(papers.map(p => p.collection)));
  const collections: Collection[] = [
    { id: "all", name: "All Papers", count: papers.length, color: C.gold, icon: "⊞" },
    ...uniqueCollections.map(c => ({
      id: c,
      name: c.charAt(0).toUpperCase() + c.slice(1),
      count: papers.filter(p => p.collection === c).length,
      color: [C.sienna, C.umber, C.green, C.inkMid, C.goldLight][uniqueCollections.indexOf(c) % 5],
      icon: ["◈", "◉", "◎", "◐", "✦"][uniqueCollections.indexOf(c) % 5]
    }))
  ];

  const filtered = activeColl === "all" ? papers : papers.filter(p => p.collection === activeColl);

  // Total size calculation (simplified)
  const totalSizeKB = dbPapers.reduce((acc, p) => {
    const size = p.file_size || "0";
    const num = parseFloat(size);
    return acc + (size.includes("MB") ? num * 1024 : num);
  }, 0);
  const sizeUsedMB = (totalSizeKB / 1024).toFixed(1);
  const usagePct = Math.min(Math.round((parseFloat(sizeUsedMB) / 5000) * 100), 100);

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

      <div className="fade-3">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 150px 60px 60px 80px", gap: 12, padding: "10px 20px", background: C.creamDark, border: `1px solid ${C.border}`, borderRadius: "4px 4px 0 0" }}>
          {["Title", "Authors", "Year", "Pages", "Added"].map(h => <span key={h} style={{ ...sectionLabel, fontSize: 10 }}>{h}</span>)}
        </div>
        {filtered.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 0", ...cardBase, borderTop: "none" }}>No papers found in this collection.</div>
        ) : (
          filtered.map((p, i) => (
            <div key={p.id} onMouseEnter={() => setHovRow(p.id)} onMouseLeave={() => setHovRow(null)} style={{ display: "grid", gridTemplateColumns: "1fr 150px 60px 60px 80px", gap: 12, padding: "13px 20px", background: hovRow === p.id ? C.white : C.creamLight, border: `1px solid ${C.border}`, borderTop: "none", transition: "all .2s", cursor: "pointer", animation: `fadeUp .4s ${i * 0.04 + 0.1}s both` }}>
              <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkDark, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.title}</span>
              <span style={{ ...bodyText, fontSize: 12.5 }}>{p.authors}</span>
              <span style={{ ...bodyText, fontSize: 12.5 }}>{p.year || "-"}</span>
              <span style={{ ...bodyText, fontSize: 12.5 }}>{p.pages}</span>
              <span style={{ ...bodyText, fontSize: 12 }}>{p.date}</span>
            </div>
          ))
        )}
      </div>

      <div className="fade-4" style={{ ...cardBase, padding: "22px 24px", marginTop: 28 }}>
        <div style={{ ...sectionLabel, fontSize: 10, marginBottom: 14 }}>Storage Usage</div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
          <span style={{ ...bodyText, fontSize: 13 }}>{sizeUsedMB} MB of 5000 MB used</span>
          <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 15, fontWeight: 700, color: C.gold }}>{usagePct}%</span>
        </div>
        <div style={{ height: 6, background: C.creamDark, border: `1px solid ${C.border}`, borderRadius: 3, overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${usagePct}%`, background: `linear-gradient(90deg, ${C.gold}, ${C.goldLight})`, borderRadius: 3 }} />
        </div>
      </div>
    </>
  );
}
