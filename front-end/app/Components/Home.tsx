"use client";

import { useState, useEffect, useRef } from "react";

// ── Typewriter Hook ──────────────────────────────────────────────
function useTypewriter(words: string[], speed = 80, pause = 2000): string {
  const [display, setDisplay] = useState("");
  const [wIdx, setWIdx] = useState(0);
  const [cIdx, setCIdx] = useState(0);
  const [del, setDel] = useState(false);

  useEffect(() => {
    const cur = words[wIdx];
    let t: ReturnType<typeof setTimeout>;
    if (!del && cIdx <= cur.length) {
      setDisplay(cur.slice(0, cIdx));
      t = setTimeout(() => setCIdx((c) => c + 1), speed);
    } else if (!del && cIdx > cur.length) {
      t = setTimeout(() => setDel(true), pause);
    } else if (del && cIdx >= 0) {
      setDisplay(cur.slice(0, cIdx));
      t = setTimeout(() => setCIdx((c) => c - 1), speed / 2.2);
    } else {
      setDel(false);
      setWIdx((w) => (w + 1) % words.length);
    }
    return () => clearTimeout(t);
  }, [cIdx, del, wIdx, words, speed, pause]);

  return display;
}

// ── Animated Counter ────────────────────────────────────────────
function Counter({ to, suffix = "" }: { to: number; suffix?: string }) {
  const [v, setV] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const started = useRef(false);

  useEffect(() => {
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && !started.current) {
        started.current = true;
        const t0 = performance.now();
        const tick = (now: number) => {
          const p = Math.min((now - t0) / 1600, 1);
          setV(Math.round((1 - Math.pow(1 - p, 3)) * to));
          if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      }
    }, { threshold: 0.5 });
    if (ref.current) io.observe(ref.current);
    return () => io.disconnect();
  }, [to]);

  return <span ref={ref}>{v.toLocaleString()}{suffix}</span>;
}

// ── Floating Paper Decoration ───────────────────────────────────
function PaperCard({ style, delay }: { style?: React.CSSProperties; delay?: string }) {
  return (
    <div style={{
      background: "#fffef9",
      border: "1px solid rgba(180,160,120,0.25)",
      borderRadius: 4,
      padding: "18px 20px",
      boxShadow: "0 8px 40px rgba(120,100,60,0.12), 0 2px 8px rgba(120,100,60,0.08)",
      animation: `floatPaper 7s ease-in-out infinite`,
      animationDelay: delay ?? "0s",
      ...style,
    }}>
      {/* Fake text lines */}
      {[100, 85, 90, 70, 95, 60].map((w, i) => (
        <div key={i} style={{
          height: 5,
          background: i === 0 ? "rgba(120,90,40,0.35)" : "rgba(180,160,120,0.2)",
          borderRadius: 3,
          width: `${w}%`,
          marginBottom: 6,
        }} />
      ))}
      <div style={{
        marginTop: 10,
        display: "inline-block",
        fontSize: 9,
        fontFamily: "'Crimson Pro', Georgia, serif",
        color: "rgba(140,110,60,0.7)",
        borderTop: "1px solid rgba(180,160,120,0.3)",
        paddingTop: 6,
        letterSpacing: "0.06em",
      }}>
        PROCESSED · GenResearch AI
      </div>
    </div>
  );
}

// ── Feature Card ────────────────────────────────────────────────
function FeatureCard({
  num, title, desc, accent,
}: { num: string; title: string; desc: string; accent: string }) {
  const [hov, setHov] = useState(false);
  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding: "32px 28px",
        border: `1px solid ${hov ? accent + "55" : "rgba(180,160,120,0.2)"}`,
        borderRadius: 4,
        background: hov ? "#fffef7" : "#faf8f2",
        transition: "all 0.35s ease",
        transform: hov ? "translateY(-4px)" : "translateY(0)",
        cursor: "default",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {hov && <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, transparent, ${accent}, transparent)`,
      }} />}
      <div style={{
        fontFamily: "'Crimson Pro', Georgia, serif",
        fontSize: 11,
        fontWeight: 600,
        color: accent,
        letterSpacing: "0.15em",
        textTransform: "uppercase",
        marginBottom: 16,
      }}>{num}</div>
      <div style={{
        fontFamily: "'Playfair Display', Georgia, serif",
        fontSize: 19,
        fontWeight: 700,
        color: "#2c1f0e",
        marginBottom: 12,
        lineHeight: 1.25,
      }}>{title}</div>
      <div style={{
        fontFamily: "'Crimson Pro', Georgia, serif",
        fontSize: 15,
        color: "#7a6040",
        lineHeight: 1.72,
      }}>{desc}</div>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────
export default function DesignA({ onNavigate, onNavigateLogin }: { onNavigate?: () => void; onNavigateLogin?: () => void }) {
  const [scrolled, setScrolled] = useState(false);
  const typed = useTypewriter([
    "Literature Reviews",
    "Research Summaries",
    "Citation Formatting",
    "Research Proposals",
    "Academic Analysis",
  ], 72, 2100);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", fn);
    return () => window.removeEventListener("scroll", fn);
  }, []);

  const features = [
    { num: "01", title: "Document Processing Engine", desc: "Upload any research PDF. Text extraction, intelligent chunking, and semantic embedding generation — all handled automatically.", accent: "#8b6914" },
    { num: "02", title: "RAG Retrieval Engine", desc: "Retrieval-Augmented Generation grounds every answer in your documents. No hallucinations — only precise, cited responses.", accent: "#6b5c38" },
    { num: "03", title: "Literature Review Agent", desc: "Analyze multiple papers at once. Structured comparative reviews that take researchers days — completed in under a minute.", accent: "#a0522d" },
    { num: "04", title: "Proposal Drafting Agent", desc: "Transform raw research ideas into polished, structured proposals with proper academic tone and logical organization.", accent: "#6b5c38" },
    { num: "05", title: "Citation Agent", desc: "Auto-extract and correctly format references in APA, MLA, IEEE, or Chicago — verified against CrossRef metadata.", accent: "#8b6914" },
    { num: "06", title: "Summarization Agent", desc: "Extract key findings, methodologies, and contributions from any paper. Dense research distilled into clear insights.", accent: "#a0522d" },
  ];

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,800;0,900;1,700&family=Crimson+Pro:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html { scroll-behavior: smooth; }
        body { background: #f5f0e8; color: #2c1f0e; font-family: 'Crimson Pro', Georgia, serif; overflow-x: hidden; }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: #f5f0e8; }
        ::-webkit-scrollbar-thumb { background: rgba(139,105,20,0.3); border-radius: 3px; }

        @keyframes fadeUp { from { opacity:0; transform:translateY(28px); } to { opacity:1; transform:translateY(0); } }
        @keyframes floatPaper {
          0%,100% { transform: translateY(0) rotate(-1.5deg); }
          50% { transform: translateY(-14px) rotate(1deg); }
        }
        @keyframes tickerCursor { 0%,100% { opacity:1; } 50% { opacity:0; } }
        @keyframes ornamentSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes lineExpand { from { width:0; } to { width: 100%; } }

        .fade1 { animation: fadeUp .8s .1s both; }
        .fade2 { animation: fadeUp .8s .25s both; }
        .fade3 { animation: fadeUp .8s .4s both; }
        .fade4 { animation: fadeUp .8s .55s both; }
        .fade5 { animation: fadeUp .8s .7s both; }
        .fade6 { animation: fadeUp .8s .9s both; }

        .nav-link { font-family: 'Crimson Pro', Georgia, serif; font-size: 15px; color: rgba(80,60,30,0.7); text-decoration: none; letter-spacing: 0.06em; transition: color .2s; }
        .nav-link:hover { color: #8b6914; }

        .btn-main { background: #2c1f0e; color: #f5f0e8; border: none; border-radius: 3px; padding: 11px 28px; font-size: 13px; font-family: 'Crimson Pro', Georgia, serif; font-weight: 600; cursor: pointer; letter-spacing: 0.08em; text-transform: uppercase; transition: all .25s; }
        .btn-main:hover { background: #8b6914; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(139,105,20,0.25); }
        .btn-outline-dark { background: transparent; color: #2c1f0e; border: 1.5px solid rgba(44,31,14,0.3); border-radius: 3px; padding: 10px 26px; font-size: 13px; font-family: 'Crimson Pro', Georgia, serif; font-weight: 500; cursor: pointer; letter-spacing: 0.06em; transition: all .25s; }
        .btn-outline-dark:hover { border-color: #8b6914; color: #8b6914; }

        .stat-box:hover { border-color: rgba(139,105,20,0.4) !important; transform: translateY(-4px); }
        .feat-card-wrap { animation: fadeUp .7s both; }
      `}</style>

      {/* NAV */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        height: 64, display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 52px",
        background: scrolled ? "rgba(245,240,232,0.96)" : "transparent",
        backdropFilter: scrolled ? "blur(16px)" : "none",
        borderBottom: scrolled ? "1px solid rgba(180,160,120,0.25)" : "1px solid transparent",
        transition: "all .4s ease",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Ornamental logo mark */}
          <div style={{
            width: 32, height: 32, position: "relative",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <div style={{
              width: 28, height: 28, border: "2px solid #8b6914",
              transform: "rotate(45deg)", position: "absolute",
            }} />
            <div style={{
              fontSize: 13, fontFamily: "'Playfair Display', serif",
              fontWeight: 700, color: "#8b6914", position: "relative", zIndex: 1,
            }}>G</div>
          </div>
          <div>
            <div style={{
              fontFamily: "'Playfair Display', serif", fontSize: 17, fontWeight: 800,
              color: "#2c1f0e", letterSpacing: "-0.01em", lineHeight: 1,
            }}>GenResearch</div>
            <div style={{
              fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 9.5,
              color: "#8b6914", letterSpacing: "0.18em", textTransform: "uppercase",
            }}>Academic AI Platform</div>
          </div>
        </div>

        <div style={{ display: "flex", gap: 32 }}>
          {[
            { label: "Features", href: "#features" },
            { label: "Agents", href: "#features" },
            { label: "Workflow", href: "#workflow" },
            { label: "About", href: "#cta" },
          ].map(l => (
            <a key={l.label} href={l.href} className="nav-link">{l.label}</a>
          ))}
        </div>

        <div style={{ display: "flex", gap: 12 }}>
          <button className="btn-outline-dark" onClick={onNavigateLogin}>Sign In</button>
          <button className="btn-main" onClick={onNavigate}>Get Started</button>
        </div>
      </nav>

      {/* HERO */}
      <section style={{
        minHeight: "100vh", display: "flex", alignItems: "center",
        padding: "130px 52px 90px", position: "relative", overflow: "hidden",
      }}>
        {/* Background texture lines */}
        <div style={{
          position: "absolute", inset: 0, pointerEvents: "none",
          backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 79px, rgba(139,105,20,0.06) 80px)",
        }} />

        {/* Decorative circle */}
        <div style={{
          position: "absolute", right: "8%", top: "15%",
          width: 480, height: 480, borderRadius: "50%",
          border: "1px solid rgba(139,105,20,0.12)",
          pointerEvents: "none",
        }} />
        <div style={{
          position: "absolute", right: "12%", top: "19%",
          width: 380, height: 380, borderRadius: "50%",
          border: "1px solid rgba(139,105,20,0.08)",
          pointerEvents: "none",
        }} />

        {/* Floating paper cards */}
        <PaperCard style={{ position: "absolute", right: "14%", top: "22%", width: 190 }} delay="0s" />
        <PaperCard style={{ position: "absolute", right: "6%", top: "52%", width: 160, transform: "rotate(3deg)" }} delay="1.5s" />

        {/* Left content */}
        <div style={{ maxWidth: 660, position: "relative", zIndex: 10 }}>
          {/* Ornamental rule */}
          <div className="fade1" style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 28 }}>
            <div style={{ height: 1, width: 40, background: "#8b6914" }} />
            <span style={{
              fontFamily: "'Crimson Pro', Georgia, serif",
              fontSize: 11, fontWeight: 600, color: "#8b6914",
              letterSpacing: "0.18em", textTransform: "uppercase",
            }}>AI Research Platform · FYP 2025</span>
            <div style={{ height: 1, width: 40, background: "#8b6914" }} />
          </div>

          <h1 className="fade2" style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: "clamp(42px, 6vw, 76px)",
            fontWeight: 900,
            color: "#2c1f0e",
            lineHeight: 1.05,
            letterSpacing: "-0.02em",
            marginBottom: 18,
          }}>
            The Intelligent<br />
            Research<br />
            <em style={{ color: "#8b6914", fontStyle: "italic" }}>Companion.</em>
          </h1>

          {/* Typewriter */}
          <div className="fade3" style={{ marginBottom: 14 }}>
            <span style={{
              fontFamily: "'Crimson Pro', Georgia, serif",
              fontSize: 22, color: "#7a6040", fontWeight: 300,
            }}>Generating </span>
            <span style={{
              fontFamily: "'Playfair Display', serif",
              fontSize: 22, fontWeight: 700, color: "#8b6914",
              borderBottom: "2px solid #8b6914",
              paddingBottom: 1,
              minWidth: 10,
              display: "inline-block",
            }}>
              {typed}
              <span style={{ animation: "tickerCursor 1s step-end infinite", borderRight: "2.5px solid #8b6914", marginLeft: 2 }} />
            </span>
            <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 22, color: "#7a6040", fontWeight: 300 }}> — automatically.</span>
          </div>

          <p className="fade3" style={{
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 17, color: "#7a6040", lineHeight: 1.8,
            maxWidth: 520, marginBottom: 44,
          }}>
            GenResearch is a multi-agent AI platform built for academics and students.
            Upload research papers, ask questions, and receive structured, cited outputs
            in seconds — not days.
          </p>

          <div className="fade4" style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 56 }}>
            <button className="btn-main" onClick={onNavigate}>Begin Research →</button>
            <button className="btn-outline-dark" onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}>View Documentation</button>
          </div>

          {/* Agent list */}
          <div className="fade5">
            <div style={{
              fontFamily: "'Crimson Pro', Georgia, serif",
              fontSize: 11, color: "#8b6914", letterSpacing: "0.18em",
              textTransform: "uppercase", marginBottom: 14,
            }}>Active Agents</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
              {[
                ["Summarization", "#8b6914"],
                ["Literature Review", "#a0522d"],
                ["Citation", "#6b5c38"],
                ["Proposal Drafting", "#8b6914"],
              ].map(([label, color]) => (
                <div key={label as string} style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "8px 16px",
                  background: "rgba(139,105,20,0.07)",
                  border: `1px solid rgba(139,105,20,0.2)`,
                  borderRadius: 2,
                }}>
                  <div style={{
                    width: 6, height: 6, borderRadius: "50%",
                    background: color as string,
                  }} />
                  <span style={{
                    fontFamily: "'Crimson Pro', Georgia, serif",
                    fontSize: 13, color: "#5a3e20", fontWeight: 500,
                  }}>{label as string}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* STATS BAND */}
      <section style={{
        padding: "60px 52px",
        background: "#2c1f0e",
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
        gap: 2,
      }}>
        {[
          { v: 95, s: "%", l: "Accuracy Rate" },
          { v: 10000, s: "+", l: "Papers Processed" },
          { v: 30, s: "s", l: "Avg. Summary Time" },
          { v: 4, s: "", l: "AI Agents" },
        ].map((st, i) => (
          <div key={i} className="stat-box" style={{
            textAlign: "center", padding: "32px 20px",
            border: "1px solid rgba(255,255,255,0.07)",
            transition: "all .3s ease", cursor: "default",
          }}>
            <div style={{
              fontFamily: "'Playfair Display', serif",
              fontSize: 46, fontWeight: 900, color: "#f5f0e8",
              lineHeight: 1, marginBottom: 8,
            }}>
              <Counter to={st.v} suffix={st.s} />
            </div>
            <div style={{
              fontFamily: "'Crimson Pro', Georgia, serif",
              fontSize: 12, color: "#8b6914",
              letterSpacing: "0.15em", textTransform: "uppercase",
            }}>{st.l}</div>
          </div>
        ))}
      </section>

      {/* FEATURES */}
      <section id="features" style={{ padding: "110px 52px", background: "#f5f0e8", scrollMarginTop: 64 }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 32, marginBottom: 64 }}>
            <div>
              <div style={{
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 11, fontWeight: 600, color: "#8b6914",
                letterSpacing: "0.18em", textTransform: "uppercase", marginBottom: 12,
              }}>Platform Architecture</div>
              <h2 style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: "clamp(32px, 4.5vw, 52px)",
                fontWeight: 900, color: "#2c1f0e",
                letterSpacing: "-0.02em", lineHeight: 1.08,
              }}>
                Eight Modules,<br />
                <em style={{ color: "#8b6914" }}>One Purpose.</em>
              </h2>
            </div>
            <div style={{
              flex: 1, maxWidth: 400,
              fontFamily: "'Crimson Pro', Georgia, serif",
              fontSize: 16, color: "#7a6040", lineHeight: 1.75,
              paddingBottom: 6,
            }}>
              Every component is purpose-built for academic research. Clean separation of concerns, independently testable, production-ready.
            </div>
          </div>
          {/* Ornamental divider */}
          <div style={{
            display: "flex", alignItems: "center", gap: 14, marginBottom: 52,
          }}>
            <div style={{ flex: 1, height: 1, background: "rgba(139,105,20,0.2)" }} />
            <div style={{
              fontFamily: "'Playfair Display', serif", fontSize: 18, color: "#8b6914",
            }}>✦</div>
            <div style={{ flex: 1, height: 1, background: "rgba(139,105,20,0.2)" }} />
          </div>

          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
            gap: 18,
          }}>
            {features.map((f, i) => (
              <div key={i} style={{ animationDelay: `${i * 0.1}s`, animation: "fadeUp .7s both" }}>
                <FeatureCard {...f} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* WORKFLOW */}
      <section id="workflow" style={{ padding: "110px 52px", background: "#efe8d8", scrollMarginTop: 64 }}>
        <div style={{ maxWidth: 900, margin: "0 auto", textAlign: "center" }}>
          <div style={{
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 11, fontWeight: 600, color: "#8b6914",
            letterSpacing: "0.18em", textTransform: "uppercase", marginBottom: 14,
          }}>Research Pipeline</div>
          <h2 style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: "clamp(30px, 4vw, 50px)",
            fontWeight: 900, color: "#2c1f0e",
            letterSpacing: "-0.02em", marginBottom: 52,
          }}>From Upload to <em style={{ color: "#8b6914" }}>Insight.</em></h2>

          <div style={{
            display: "flex", justifyContent: "center",
            flexWrap: "wrap", gap: 0, position: "relative",
          }}>
            {[
              { n: "I", label: "Upload Papers", sub: "PDF ingestion" },
              { n: "II", label: "Semantic Index", sub: "Vector embeddings" },
              { n: "III", label: "Agent Routing", sub: "Task dispatch" },
              { n: "IV", label: "RAG Retrieval", sub: "Context grounding" },
              { n: "V", label: "Output Ready", sub: "Structured results" },
            ].map((s, i, arr) => (
              <div key={i} style={{
                display: "flex", alignItems: "center",
              }}>
                <div style={{ textAlign: "center", padding: "0 18px" }}>
                  <div style={{
                    width: 52, height: 52, borderRadius: "50%",
                    border: "2px solid #8b6914",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    margin: "0 auto 12px",
                    background: "#f5f0e8",
                  }}>
                    <span style={{
                      fontFamily: "'Playfair Display', serif",
                      fontSize: 14, fontWeight: 700, color: "#8b6914",
                    }}>{s.n}</span>
                  </div>
                  <div style={{
                    fontFamily: "'Playfair Display', serif",
                    fontSize: 13, fontWeight: 700, color: "#2c1f0e", marginBottom: 4,
                  }}>{s.label}</div>
                  <div style={{
                    fontFamily: "'Crimson Pro', Georgia, serif",
                    fontSize: 12, color: "#8b6914",
                  }}>{s.sub}</div>
                </div>
                {i < arr.length - 1 && (
                  <div style={{
                    width: 28, height: 1,
                    background: "linear-gradient(90deg, #8b6914, rgba(139,105,20,0.3))",
                    marginTop: -28,
                  }} />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TECH + CTA */}
      <section id="cta" style={{ padding: "90px 52px", background: "#f5f0e8", textAlign: "center", scrollMarginTop: 64 }}>
        <div style={{
          fontFamily: "'Crimson Pro', Georgia, serif",
          fontSize: 11, color: "#8b6914", letterSpacing: "0.18em",
          textTransform: "uppercase", marginBottom: 28,
        }}>Built With</div>
        <div style={{
          display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 12, marginBottom: 72,
          maxWidth: 700, margin: "0 auto 72px",
        }}>
          {["React · Next.js", "TypeScript", "FastAPI", "LangChain", "LangGraph", "ChromaDB", "PyPDF", "OpenAI", "Supabase Auth"].map(t => (
            <span key={t} style={{
              padding: "7px 16px",
              border: "1px solid rgba(139,105,20,0.2)",
              borderRadius: 2,
              fontFamily: "'Crimson Pro', Georgia, serif",
              fontSize: 13.5, color: "#7a6040",
              background: "#efe8d8",
            }}>{t}</span>
          ))}
        </div>

        <div style={{
          maxWidth: 580, margin: "0 auto",
          padding: "56px 48px",
          border: "1px solid rgba(139,105,20,0.25)",
          background: "#2c1f0e",
          borderRadius: 4,
        }}>
          <div style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: "clamp(26px, 3.5vw, 40px)",
            fontWeight: 900, color: "#f5f0e8",
            marginBottom: 16, lineHeight: 1.2,
          }}>
            Begin Your Research<br />
            <em style={{ color: "#c8971e" }}>Journey Today.</em>
          </div>
          <p style={{
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 16, color: "rgba(245,240,232,0.65)",
            lineHeight: 1.75, marginBottom: 32,
          }}>
            Join researchers and students who use GenResearch to save hours on every paper.
          </p>
          <button className="btn-main" style={{ background: "#8b6914" }} onClick={onNavigate}>
            Get Started Free →
          </button>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{
        padding: "28px 52px",
        background: "#1e1408",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        flexWrap: "wrap", gap: 14,
      }}>
        <span style={{
          fontFamily: "'Playfair Display', serif",
          fontSize: 15, fontWeight: 800, color: "#c8971e",
        }}>GenResearch</span>
        <span style={{
          fontFamily: "'Crimson Pro', Georgia, serif",
          fontSize: 13, color: "rgba(200,151,30,0.45)",
        }}>
          Ali Ahmed · Kaleem-Ullah Abbasi · COMSATS WAH · BSE SP23 · FYP 2025
        </span>
        <div style={{ display: "flex", gap: 20 }}>
          {["Privacy", "Terms", "GitHub"].map(l => (
            <a key={l} href="#" style={{
              fontFamily: "'Crimson Pro', Georgia, serif",
              fontSize: 13, color: "rgba(200,151,30,0.45)",
              textDecoration: "none", transition: "color .2s",
            }}
              onMouseEnter={e => (e.currentTarget.style.color = "#c8971e")}
              onMouseLeave={e => (e.currentTarget.style.color = "rgba(200,151,30,0.45)")}
            >{l}</a>
          ))}
        </div>
      </footer>
    </>
  );
}
