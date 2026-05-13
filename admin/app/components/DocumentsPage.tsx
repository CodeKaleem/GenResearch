"use client";
import { useState } from "react";
import { C, Badge, SectionHead, PageTitle, Modal, Field, inputStyle, selectStyle, Bar, Num } from "./shared";

interface Doc {
  id: string; title: string; author: string; year: string;
  pages: number; chunks: number; size: string;
  status: "indexed" | "processing" | "failed";
  collection: string; uploaded: string; uploadedBy: string;
}

const INITIAL_DOCS: Doc[] = [
  { id: "1",  title: "BERT: Pre-training of Deep Bidirectional Transformers",          author: "Devlin et al.", year: "2018", pages: 16,  chunks: 124, size: "2.1 MB",  status: "indexed",    collection: "NLP Foundations",     uploaded: "2 hours ago",  uploadedBy: "Ali Ahmed" },
  { id: "2",  title: "Attention Is All You Need",                                       author: "Vaswani et al.", year: "2017", pages: 11,  chunks: 88,  size: "1.4 MB",  status: "indexed",    collection: "NLP Foundations",     uploaded: "3 hours ago",  uploadedBy: "Kaleem Abbasi" },
  { id: "3",  title: "A Survey on Knowledge Graphs",                                   author: "Hogan et al.",   year: "2021", pages: 78,  chunks: 612, size: "8.8 MB",  status: "indexed",    collection: "Knowledge Graphs",    uploaded: "Yesterday",    uploadedBy: "Sara Malik" },
  { id: "4",  title: "Retrieval-Augmented Generation for NLP",                         author: "Lewis et al.",   year: "2020", pages: 13,  chunks: 102, size: "1.8 MB",  status: "indexed",    collection: "RAG Research",        uploaded: "2 days ago",   uploadedBy: "Nadia Khan" },
  { id: "5",  title: "Large Language Models: A Survey",                                author: "Zhao et al.",    year: "2023", pages: 58,  chunks: 460, size: "6.3 MB",  status: "processing", collection: "LLM Studies",         uploaded: "10 min ago",   uploadedBy: "Usman Qureshi" },
  { id: "6",  title: "Emerging Contaminants in Water Treatment",                       author: "Ahmed et al.",   year: "2022", pages: 22,  chunks: 178, size: "3.2 MB",  status: "indexed",    collection: "Environmental Sci",   uploaded: "1 week ago",   uploadedBy: "Fatima Zahra" },
  { id: "7",  title: "Deep Learning for Medical Image Segmentation",                   author: "Ronneberger",    year: "2015", pages: 9,   chunks: 72,  size: "1.1 MB",  status: "failed",     collection: "Medical AI",          uploaded: "3 days ago",   uploadedBy: "Hamza Tariq" },
  { id: "8",  title: "Graph Neural Networks: A Review of Methods",                     author: "Zhou et al.",    year: "2020", pages: 18,  chunks: 144, size: "2.4 MB",  status: "indexed",    collection: "Graph Learning",      uploaded: "4 days ago",   uploadedBy: "Ali Ahmed" },
];

const COLLECTIONS = ["All Collections", "NLP Foundations", "RAG Research", "LLM Studies", "Knowledge Graphs", "Environmental Sci", "Medical AI", "Graph Learning"];

function DocRow({ doc, onDelete, onReindex }: { doc: Doc; onDelete: (d: Doc) => void; onReindex: (d: Doc) => void }) {
  const [hov, setHov] = useState(false);
  const [menu, setMenu] = useState(false);
  const sc = { indexed: C.green, processing: C.goldLight, failed: C.red }[doc.status];
  return (
    <div onMouseEnter={() => setHov(true)} onMouseLeave={() => { setHov(false); setMenu(false); }}
      style={{ display: "grid", gridTemplateColumns: "3fr 1.2fr 80px 80px 80px 110px 110px 50px", alignItems: "center", padding: "13px 16px", background: hov ? C.white : "transparent", borderBottom: `1px solid ${C.border}`, transition: "background .2s", position: "relative" }}>
      <div>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, fontWeight: 500, color: C.inkDark, marginBottom: 2 }}>{doc.title}</div>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11.5, color: C.inkLight }}>{doc.author} · {doc.year}</div>
      </div>
      <div>
        <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: C.umber, background: `${C.umber}14`, border: `1px solid ${C.umber}22`, borderRadius: 2, padding: "2px 8px" }}>{doc.collection}</span>
      </div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight, textAlign: "center" }}>{doc.pages}</div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight, textAlign: "center" }}>{doc.chunks}</div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight, textAlign: "center" }}>{doc.size}</div>
      <div><Badge label={doc.status} color={sc} pulse={doc.status === "processing"} /></div>
      <div>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.inkLight }}>{doc.uploaded}</div>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: C.inkLight }}>by {doc.uploadedBy}</div>
      </div>
      <div style={{ position: "relative" }}>
        <button onClick={() => setMenu(m => !m)} style={{ background: "transparent", border: "none", cursor: "pointer", color: C.inkLight, fontSize: 16, padding: "2px 6px", borderRadius: 3 }}
          onMouseEnter={e => (e.currentTarget.style.background = C.creamDark)}
          onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
        >⋮</button>
        {menu && (
          <div style={{ position: "absolute", right: 0, top: "100%", zIndex: 50, background: C.white, border: `1px solid ${C.borderGold}`, borderRadius: 4, boxShadow: `0 8px 24px ${C.shadowMd}`, minWidth: 150, overflow: "hidden" }}>
            {[
              { label: "⟳ Re-index", color: C.gold,    action: () => { onReindex(doc); setMenu(false); } },
              { label: "↓ Download", color: C.inkDark,  action: () => setMenu(false) },
              { label: "✕ Delete",   color: C.red,      action: () => { onDelete(doc); setMenu(false); } },
            ].map(item => (
              <button key={item.label} onClick={item.action} style={{ display: "block", width: "100%", textAlign: "left", padding: "10px 14px", background: "transparent", border: "none", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: item.color, cursor: "pointer" }}
                onMouseEnter={e => (e.currentTarget.style.background = C.creamDark)}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
              >{item.label}</button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function UploadModal({ onClose, onUpload }: { onClose: () => void; onUpload: (d: Doc) => void }) {
  const [title, setTitle] = useState(""); const [author, setAuthor] = useState(""); const [year, setYear] = useState("");
  const [collection, setCollection] = useState("NLP Foundations"); const [file, setFile] = useState("");

  const handle = () => {
    if (!title) return;
    onUpload({ id: Date.now().toString(), title, author: author || "Unknown", year: year || "2025", pages: Math.floor(Math.random() * 40) + 5, chunks: 0, size: "—", status: "processing", collection, uploaded: "Just now", uploadedBy: "Admin" });
    onClose();
  };

  return (
    <Modal title="Upload Document" onClose={onClose}>
      <Field label="Paper Title"><input style={inputStyle} placeholder="e.g. A Survey on Large Language Models" value={title} onChange={e => setTitle(e.target.value)} /></Field>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Field label="Author(s)"><input style={inputStyle} placeholder="Smith et al." value={author} onChange={e => setAuthor(e.target.value)} /></Field>
        <Field label="Year"><input style={inputStyle} placeholder="2024" value={year} onChange={e => setYear(e.target.value)} /></Field>
      </div>
      <Field label="Collection">
        <select style={selectStyle} value={collection} onChange={e => setCollection(e.target.value)}>
          {COLLECTIONS.slice(1).map(c => <option key={c}>{c}</option>)}
        </select>
      </Field>
      <Field label="PDF File">
        <div style={{ border: `2px dashed ${C.borderGold}`, borderRadius: 3, padding: "24px", textAlign: "center", background: C.goldFaint, cursor: "pointer" }}
          onClick={() => setFile("paper.pdf")}
        >
          <div style={{ fontSize: 24, marginBottom: 8 }}>📄</div>
          <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkLight }}>{file || "Click to select PDF — or drag & drop"}</div>
        </div>
      </Field>
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 20 }}>
        <button className="btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn-gold" onClick={handle}>Upload & Index</button>
      </div>
    </Modal>
  );
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>(INITIAL_DOCS);
  const [search, setSearch] = useState("");
  const [collectionFilter, setCollectionFilter] = useState("All Collections");
  const [statusFilter, setStatusFilter] = useState("All");
  const [showUpload, setShowUpload] = useState(false);
  const [toast, setToast] = useState("");

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3000); };

  const filtered = docs.filter(d => {
    const q = search.toLowerCase();
    const matchQ = !q || d.title.toLowerCase().includes(q) || d.author.toLowerCase().includes(q) || d.collection.toLowerCase().includes(q);
    const matchC = collectionFilter === "All Collections" || d.collection === collectionFilter;
    const matchS = statusFilter === "All" || d.status === statusFilter;
    return matchQ && matchC && matchS;
  });

  const totalChunks = docs.reduce((s, d) => s + d.chunks, 0);
  const indexed = docs.filter(d => d.status === "indexed").length;
  const failed = docs.filter(d => d.status === "failed").length;

  return (
    <div style={{ animation: "fadeUp .5s both" }}>
      <PageTitle
        title="Documents & Index"
        sub="Knowledge Base"
        actions={<><button className="btn-ghost" onClick={() => { setDocs(prev => prev.map(d => d.status === "failed" ? { ...d, status: "processing" as const } : d)); showToast("Re-indexing all failed documents…"); }}>⟳ Rebuild Index</button><button className="btn-gold" onClick={() => setShowUpload(true)}>↑ Upload Paper</button></>}
      />

      {toast && <div style={{ position: "fixed", bottom: 28, right: 28, zIndex: 900, background: C.inkDark, color: C.cream, padding: "12px 20px", borderRadius: 4, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, boxShadow: `0 8px 24px ${C.shadowMd}`, animation: "fadeUp .3s both" }}><span style={{ color: C.green }}>✓</span> {toast}</div>}

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 24 }}>
        {[
          { label: "Total Papers",   value: docs.length,  color: C.gold },
          { label: "Total Chunks",   value: totalChunks,  color: C.sienna },
          { label: "Indexed",        value: indexed,      color: C.green },
          { label: "Failed",         value: failed,       color: C.red },
        ].map(s => (
          <div key={s.label} className="card" style={{ padding: "16px 18px" }}>
            <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 26, fontWeight: 900, color: s.color }}><Num to={s.value} /></div>
            <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.inkLight, letterSpacing: "0.10em", textTransform: "uppercase", marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      <div className="card">
        {/* Toolbar */}
        <div style={{ padding: "14px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ position: "relative", flex: 1, minWidth: 200 }}>
            <span style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: C.inkLight, fontSize: 13 }}>🔍</span>
            <input placeholder="Search documents…" value={search} onChange={e => setSearch(e.target.value)}
              style={{ ...inputStyle, paddingLeft: 32 }}
              onFocus={e => (e.target.style.borderColor = C.gold)}
              onBlur={e => (e.target.style.borderColor = C.border)}
            />
          </div>
          <select style={{ ...selectStyle, width: "auto", minWidth: 160 }} value={collectionFilter} onChange={e => setCollectionFilter(e.target.value)}>
            {COLLECTIONS.map(c => <option key={c}>{c}</option>)}
          </select>
          <select style={{ ...selectStyle, width: "auto", minWidth: 130 }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option value="All">All Statuses</option>
            <option value="indexed">Indexed</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
          </select>
          <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.inkLight }}>{filtered.length} document(s)</span>
        </div>

        {/* Header */}
        <div style={{ display: "grid", gridTemplateColumns: "3fr 1.2fr 80px 80px 80px 110px 110px 50px", padding: "9px 16px", background: C.creamDark, borderBottom: `1.5px solid ${C.border}` }}>
          {["Title", "Collection", "Pages", "Chunks", "Size", "Status", "Uploaded", ""].map((h, i) => (
            <span key={i} style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, fontWeight: 600, color: C.gold, letterSpacing: "0.12em", textTransform: "uppercase" }}>{h}</span>
          ))}
        </div>

        {filtered.length === 0
          ? <div style={{ padding: 40, textAlign: "center", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, color: C.inkLight }}>No documents match your search.</div>
          : filtered.map(d => (
            <DocRow key={d.id} doc={d}
              onDelete={doc => { setDocs(prev => prev.filter(x => x.id !== doc.id)); showToast(`"${doc.title}" deleted`); }}
              onReindex={doc => { setDocs(prev => prev.map(x => x.id === doc.id ? { ...x, status: "processing" as const } : x)); showToast(`Re-indexing "${doc.title}"…`); }}
            />
          ))
        }
      </div>

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} onUpload={d => { setDocs(prev => [d, ...prev]); showToast("Document uploaded and queued for indexing"); }} />}
    </div>
  );
}
