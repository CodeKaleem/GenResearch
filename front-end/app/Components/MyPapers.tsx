"use client";

import { useState, useEffect } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";
import { getCurrentUserId, subscribeToPapers, type Paper as DBPaper } from "../../lib/db";

interface Paper {
  id: string; title: string; authors: string; year: number;
  pages: number; tags: string[]; status: "indexed" | "processing" | "unread" | "failed"; addedDate: string;
}

function StatusBadge({ status }: { status: Paper["status"] }) {
  const m = {
    indexed: { l: "Indexed", c: C.green },
    processing: { l: "Processing", c: C.gold },
    unread: { l: "Unread", c: C.umber },
    failed: { l: "Failed", c: C.red }
  };
  const s = m[status] || m.unread;
  return <span style={{ padding: "3px 10px", borderRadius: 2, background: `${s.c}15`, border: `1px solid ${s.c}33`, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: s.c, letterSpacing: "0.08em", textTransform: "uppercase" }}>{s.l}</span>;
}

function PaperCard({ paper }: { paper: Paper }) {
  const [hov, setHov] = useState(false);

  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const uid = await getCurrentUserId();
    if (!uid) return alert("Session expired.");
    window.open(`http://localhost:8000/papers/${paper.id}/download?user_id=${uid}`, "_blank");
  };

  return (
    <div onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)} style={{ ...cardBase, padding: "22px", background: hov ? C.white : C.creamLight, borderColor: hov ? C.borderGold : C.border, transform: hov ? "translateY(-3px)" : "none", boxShadow: hov ? `0 8px 24px ${C.shadow}` : "none", cursor: "pointer" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <StatusBadge status={paper.status} />
        <span style={{ ...bodyText, fontSize: 12 }}>{paper.year}</span>
      </div>
      <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 15, fontWeight: 700, color: C.inkDark, lineHeight: 1.3, marginBottom: 8, minHeight: 40 }}>{paper.title}</div>
      <div style={{ ...bodyText, fontSize: 12.5, marginBottom: 8 }}>{paper.authors}</div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        <span style={{ ...bodyText, fontSize: 12 }}>{paper.pages} pages</span>
        <span style={{ ...bodyText, fontSize: 11 }}>{paper.addedDate}</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
          {paper.tags.map(t => <span key={t} style={{ padding: "2px 8px", borderRadius: 2, background: C.goldFaint, border: `1px solid ${C.gold}22`, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10.5, color: C.gold }}>{t}</span>)}
        </div>
        <button
          onClick={handleDownload}
          title="Download PDF"
          style={{
            padding: "4px 10px", borderRadius: 3, border: `1px solid ${C.gold}55`,
            background: C.goldFaint, color: C.gold, fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 11, fontWeight: 600, cursor: "pointer", transition: "all .2s"
          }}
          onMouseEnter={(e) => { (e.target as HTMLButtonElement).style.background = C.gold; (e.target as HTMLButtonElement).style.color = C.white; }}
          onMouseLeave={(e) => { (e.target as HTMLButtonElement).style.background = C.goldFaint; (e.target as HTMLButtonElement).style.color = C.gold; }}
        >
          ⬇ PDF
        </button>
      </div>
    </div>
  );
}

export default function MyPapers() {
  const [dbPapers, setDbPapers] = useState<DBPaper[]>([]);
  const [search, setSearch] = useState("");
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<"date" | "title" | "year">("date");

  useEffect(() => {
    let isMounted = true;
    let unsub: (() => void) | undefined;
    getCurrentUserId().then(uid => {
      if (uid && isMounted) unsub = subscribeToPapers(uid, setDbPapers);
    });
    return () => {
      isMounted = false;
      unsub?.();
    };
  }, []);

  const papers: Paper[] = dbPapers.map(p => ({
    id: p.id,
    title: p.title,
    authors: p.authors,
    year: p.year || 0,
    pages: p.pages,
    tags: p.tags,
    status: p.status,
    addedDate: new Date(p.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
  }));

  const allTags = Array.from(new Set(papers.flatMap(p => p.tags)));

  const filtered = papers.filter(p => {
    const q = search.toLowerCase();
    return (!q || p.title.toLowerCase().includes(q) || p.authors.toLowerCase().includes(q)) && (!activeTag || p.tags.includes(activeTag));
  }).sort((a, b) => sortBy === "title" ? a.title.localeCompare(b.title) : sortBy === "year" ? b.year - a.year : 0);

  return (
    <>
      <div className="fade-1" style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ height: 1, width: 28, background: C.gold }} />
          <span style={{ ...sectionLabel }}>Research Collection</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1 style={{ ...headingStyle, fontSize: "clamp(24px, 3vw, 34px)" }}>My <em style={{ color: C.gold }}>Papers</em></h1>
            <p style={{ ...bodyText, fontSize: 14, marginTop: 4 }}>{papers.length} papers in your library</p>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn-outline" style={{ padding: "7px 16px", fontSize: 11.5 }} onClick={() => alert("Exporting " + papers.length + " papers…")}>Export All</button>
            <button className="btn-gold" style={{ padding: "7px 16px", fontSize: 11.5 }} onClick={() => alert("Upload dialog would open here")}>+ Upload</button>
          </div>
        </div>
      </div>

      <div className="fade-2" style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ position: "relative", flex: 1, minWidth: 200 }}>
          <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: C.inkLight, fontSize: 13 }}>🔍</span>
          <input placeholder="Search papers…" value={search} onChange={e => setSearch(e.target.value)} style={{ width: "100%", padding: "9px 14px 9px 34px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: C.white, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkDark, outline: "none" }} onFocus={e => (e.target.style.borderColor = C.gold)} onBlur={e => (e.target.style.borderColor = C.border)} />
        </div>
        <select value={sortBy} onChange={e => setSortBy(e.target.value as "date"|"title"|"year")} style={{ padding: "9px 14px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: C.white, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkDark, outline: "none", cursor: "pointer" }}>
          <option value="date">Sort by Date</option>
          <option value="title">Sort by Title</option>
          <option value="year">Sort by Year</option>
        </select>
      </div>

      <div className="fade-2" style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 24 }}>
        <button onClick={() => setActiveTag(null)} style={{ padding: "5px 14px", borderRadius: 2, cursor: "pointer", border: `1px solid ${!activeTag ? C.gold : C.border}`, background: !activeTag ? C.goldFaint : "transparent", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, fontWeight: !activeTag ? 600 : 400, color: !activeTag ? C.gold : C.inkLight }}>All</button>
        {allTags.map(tag => <button key={tag} onClick={() => setActiveTag(activeTag === tag ? null : tag)} style={{ padding: "5px 14px", borderRadius: 2, cursor: "pointer", border: `1px solid ${activeTag === tag ? C.gold : C.border}`, background: activeTag === tag ? C.goldFaint : "transparent", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, fontWeight: activeTag === tag ? 600 : 400, color: activeTag === tag ? C.gold : C.inkLight }}>{tag}</button>)}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 24 }}>
        <div style={{ flex: 1, height: 1, background: C.border }} />
        <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, color: C.gold }}>✦</div>
        <div style={{ flex: 1, height: 1, background: C.border }} />
      </div>

      <div className="fade-3" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
        {filtered.map((p, i) => <div key={p.id} style={{ animation: `fadeUp .5s ${i * 0.05 + 0.1}s both` }}><PaperCard paper={p} /></div>)}
      </div>

      {filtered.length === 0 && <div style={{ textAlign: "center", padding: "60px 20px", ...bodyText, fontSize: 15 }}>No papers match your search criteria.</div>}
    </>
  );
}
