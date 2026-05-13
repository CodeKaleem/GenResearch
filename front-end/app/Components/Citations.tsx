"use client";

import { useState } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";

type CitationFormat = "APA" | "MLA" | "IEEE" | "Chicago";

interface Citation {
  id: string; authors: string; year: string; title: string;
  source: string; doi?: string;
}

const citations: Citation[] = [
  { id: "1", authors: "Vaswani, A., Shazeer, N., Parmar, N., et al.", year: "2017", title: "Attention Is All You Need", source: "Advances in Neural Information Processing Systems, 30", doi: "10.48550/arXiv.1706.03762" },
  { id: "2", authors: "Devlin, J., Chang, M., Lee, K., & Toutanova, K.", year: "2019", title: "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding", source: "Proceedings of NAACL-HLT, pp. 4171–4186", doi: "10.18653/v1/N19-1423" },
  { id: "3", authors: "Brown, T. B., Mann, B., Ryder, N., et al.", year: "2020", title: "Language Models are Few-Shot Learners", source: "Advances in Neural Information Processing Systems, 33", doi: "10.48550/arXiv.2005.14165" },
  { id: "4", authors: "He, K., Zhang, X., Ren, S., & Sun, J.", year: "2016", title: "Deep Residual Learning for Image Recognition", source: "Proceedings of the IEEE Conference on CVPR, pp. 770–778" },
  { id: "5", authors: "Dosovitskiy, A., Beyer, L., Kolesnikov, A., et al.", year: "2021", title: "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale", source: "Proceedings of ICLR" },
  { id: "6", authors: "Wei, J., Wang, X., Schuurmans, D., et al.", year: "2022", title: "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models", source: "Advances in Neural Information Processing Systems, 35" },
  { id: "7", authors: "Hu, E., Shen, Y., Wallis, P., et al.", year: "2022", title: "LoRA: Low-Rank Adaptation of Large Language Models", source: "Proceedings of ICLR" },
  { id: "8", authors: "Touvron, H., Lavril, T., Izacard, G., et al.", year: "2023", title: "LLaMA: Open and Efficient Foundation Language Models", source: "arXiv preprint arXiv:2302.13971" },
];

function formatCitation(c: Citation, fmt: CitationFormat): string {
  switch (fmt) {
    case "APA": return `${c.authors} (${c.year}). ${c.title}. ${c.source}.${c.doi ? ` https://doi.org/${c.doi}` : ""}`;
    case "MLA": return `${c.authors.split(",")[0]}, et al. "${c.title}." ${c.source} (${c.year}).`;
    case "IEEE": return `${c.authors}, "${c.title}," ${c.source}, ${c.year}.`;
    case "Chicago": return `${c.authors}. "${c.title}." ${c.source} (${c.year}).`;
  }
}

function CitationRow({ c, fmt, idx }: { c: Citation; fmt: CitationFormat; idx: number }) {
  const [hov, setHov] = useState(false);
  const [copied, setCopied] = useState(false);
  const text = formatCitation(c, fmt);
  const handleCopy = () => { navigator.clipboard.writeText(text).catch(() => {}); setCopied(true); setTimeout(() => setCopied(false), 1500); };

  return (
    <div onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)} style={{ display: "flex", gap: 14, padding: "16px 20px", background: hov ? C.white : "transparent", borderBottom: `1px solid ${C.border}`, transition: "all .2s", alignItems: "flex-start" }}>
      <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 13, fontWeight: 700, color: C.gold, minWidth: 24, flexShrink: 0 }}>[{idx}]</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkDark, lineHeight: 1.6 }}>{text}</div>
        {c.doi && <div style={{ ...bodyText, fontSize: 11, marginTop: 3, color: C.gold }}>DOI: {c.doi}</div>}
      </div>
      <button onClick={handleCopy} style={{ flexShrink: 0, padding: "5px 12px", borderRadius: 2, border: `1px solid ${copied ? C.green : C.border}`, background: copied ? `${C.green}15` : "transparent", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: copied ? C.green : C.inkLight, cursor: "pointer", transition: "all .2s" }}>
        {copied ? "Copied ✓" : "Copy"}
      </button>
    </div>
  );
}

export default function Citations() {
  const [format, setFormat] = useState<CitationFormat>("APA");
  const formats: CitationFormat[] = ["APA", "MLA", "IEEE", "Chicago"];

  return (
    <>
      <div className="fade-1" style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ height: 1, width: 28, background: C.gold }} />
          <span style={{ ...sectionLabel }}>Reference Management</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1 style={{ ...headingStyle, fontSize: "clamp(24px, 3vw, 34px)" }}>Extracted <em style={{ color: C.gold }}>Citations</em></h1>
            <p style={{ ...bodyText, fontSize: 14, marginTop: 4 }}>{citations.length} references extracted and verified</p>
          </div>
          <button className="btn-gold" style={{ padding: "8px 18px", fontSize: 11.5 }} onClick={() => alert("Exporting all citations in " + format + " format…")}>Export All ({format})</button>
        </div>
      </div>

      {/* Format selector */}
      <div className="fade-2" style={{ display: "flex", gap: 6, marginBottom: 24 }}>
        {formats.map(f => (
          <button key={f} onClick={() => setFormat(f)} style={{ padding: "7px 20px", borderRadius: 2, cursor: "pointer", border: `1px solid ${format === f ? C.gold : C.border}`, background: format === f ? C.goldFaint : "transparent", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, fontWeight: format === f ? 600 : 400, color: format === f ? C.gold : C.inkLight, transition: "all .2s", letterSpacing: "0.05em" }}>{f}</button>
        ))}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 24 }}>
        <div style={{ flex: 1, height: 1, background: C.border }} />
        <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, color: C.gold }}>✦</div>
        <div style={{ flex: 1, height: 1, background: C.border }} />
      </div>

      {/* Preview panel */}
      <div className="fade-3" style={{ ...cardBase, marginBottom: 28, overflow: "hidden" }}>
        <div style={{ padding: "14px 20px", background: C.creamDark, borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ ...sectionLabel, fontSize: 10 }}>References — {format} Format</span>
          <span style={{ ...bodyText, fontSize: 12 }}>{citations.length} entries</span>
        </div>
        {citations.map((c, i) => (
          <div key={c.id} style={{ animation: `fadeUp .4s ${i * 0.04 + 0.1}s both` }}>
            <CitationRow c={c} fmt={format} idx={i + 1} />
          </div>
        ))}
      </div>

      {/* Tip */}
      <div className="fade-4" style={{ padding: "20px 24px", background: C.inkDark, borderRadius: 4, display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, fontWeight: 700, color: C.goldLight }}>✦ Tip</span>
        <span style={{ ...bodyText, fontSize: 13.5, color: "rgba(245,240,232,0.72)", flex: 1 }}>
          Citations are verified against CrossRef metadata when a DOI is available. Switch formats instantly — no re-processing needed.
        </span>
      </div>
    </>
  );
}
