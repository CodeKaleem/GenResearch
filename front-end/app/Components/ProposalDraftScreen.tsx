"use client";
import { useState, useEffect } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";
import { getCurrentUserId, getUserPapers, type Paper } from "../../lib/db";
import { exportToPDF, exportToDOCX } from "../../lib/exportUtils";

const API = "http://localhost:8000";

export default function ProposalDraftScreen({ onBack }: { onBack: () => void }) {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"proposal" | "analysis" | "logs">("logs");
  const [liveState, setLiveState] = useState<{ current_step: string; steps_log: string[] }>({ current_step: "", steps_log: [] });
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [awaitingApproval, setAwaitingApproval] = useState(false);
  const [awaitingQuestionnaire, setAwaitingQuestionnaire] = useState(false);
  const [awaitingScrapePermission, setAwaitingScrapePermission] = useState(false);
  
  const [questions, setQuestions] = useState<any[]>([]);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [approvalComment, setApprovalComment] = useState("");
  
  const [outline, setOutline] = useState<any>(null);
  const [sources, setSources] = useState<any[]>([]);

  useEffect(() => {
    getCurrentUserId().then(uid => {
      setUserId(uid);
      if (uid) getUserPapers(uid).then(({ data }) => setPapers(data.filter(p => p.status === "indexed")));
    });
  }, []);

  const toggle = (id: string) => {
    setSelected(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; });
  };

  const run = async () => {
    if (!userId || selected.size === 0 || !topic.trim()) return;
    setLoading(true); setResult(null); setActiveTab("logs"); 
    setAwaitingApproval(false); setAwaitingQuestionnaire(false); setAwaitingScrapePermission(false);
    setLiveState({ current_step: "starting", steps_log: ["⚡ Pipeline started"] });
    
    try {
      const res = await fetch(`${API}/pipeline/start`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, paper_ids: [...selected], topic, citation_style: "apa" }),
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      setSessionId(data.session_id);
      
      startStream(data.session_id);
    } catch (e: any) { 
      setResult({ error: e.message }); 
      setLoading(false);
    }
  };

  const startStream = async (sid: string) => {
    try {
      const res = await fetch(`${API}/pipeline/${sid}/stream`);
      if (!res.ok) throw new Error(`Error ${res.status}`);
      
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No reader");

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            if (data.type === "state_update") {
              setLiveState(data.state);
            } else if (data.type === "interrupt") {
              if (data.reason === "awaiting_questionnaire") {
                setAwaitingQuestionnaire(true);
                setQuestions(data.questions || []);
              } else if (data.reason === "awaiting_scrape_permission") {
                setAwaitingScrapePermission(true);
              } else if (data.reason === "awaiting_approval") {
                setAwaitingApproval(true);
                setOutline(data.outline);
                setSources(data.sources || []);
              }
              setLoading(false);
              return; // stop reading this stream, wait for user
            } else if (data.type === "done") {
              setResult(data.final_state);
              setActiveTab("proposal");
              setLoading(false);
            } else if (data.type === "error") {
              setResult({ error: data.message });
              setLoading(false);
            }
          } catch (e) {
            console.error("Failed to parse stream JSON", line);
          }
        }
      }
    } catch (e: any) { 
      setResult({ error: e.message }); 
      setLoading(false);
    }
  };

  const submitQuestionnaire = async () => {
    if (!sessionId) return;
    setAwaitingQuestionnaire(false);
    setLoading(true);
    try {
      const res = await fetch(`${API}/pipeline/${sessionId}/questionnaire`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers })
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      startStream(sessionId);
    } catch (e: any) { setResult({ error: e.message }); setLoading(false); }
  };

  const submitScrapePermission = async (granted: boolean) => {
    if (!sessionId) return;
    setAwaitingScrapePermission(false);
    setLoading(true);
    try {
      const res = await fetch(`${API}/pipeline/${sessionId}/scrape-permission`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ granted })
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      startStream(sessionId);
    } catch (e: any) { setResult({ error: e.message }); setLoading(false); }
  };

  const approve = async () => {
    if (!sessionId) return;
    setAwaitingApproval(false);
    setLoading(true);
    try {
      const res = await fetch(`${API}/pipeline/${sessionId}/approve`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved: true, approval_comment: approvalComment })
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      startStream(sessionId);
    } catch (e: any) {
      setResult({ error: e.message });
      setLoading(false);
    }
  };

  const stepsList = [
    { id: "topic_input", label: "Topic Input", agent: "Orchestrator" },
    { id: "questionnaire", label: "Questionnaire", agent: "Nano 3B" },
    { id: "sufficiency_eval", label: "Sufficiency Check", agent: "Nano 3B" },
    { id: "gap_report", label: "Gap Report", agent: "Nano 3B" },
    { id: "outline_plan", label: "Outline / Plan", agent: "Nano 3B" },
    { id: "source_gathering", label: "Source Fetching", agent: "Tool" },
    { id: "source_quality_eval", label: "Source Quality", agent: "Nano 3B" },
    { id: "ingestion", label: "Registry Ingestion", agent: "Tool" },
    { id: "user_approval", label: "Human Checkpoint", agent: "User" },
    { id: "draft", label: "Draft Generation", agent: "Lightning 30B" },
    { id: "citation_verify", label: "Citation Verify", agent: "Nano 3B" },
    { id: "section_critic", label: "Quality Critic", agent: "Nano 3B" },
    { id: "final_qa", label: "Final QA", agent: "Nano 3B" },
    { id: "output", label: "Docx Generation", agent: "Tool" }
  ];

  const cancel = async () => {
    setLoading(false);
    setAwaitingApproval(false);
    setAwaitingQuestionnaire(false);
    setAwaitingScrapePermission(false);
    setLiveState(prev => ({
      ...prev,
      steps_log: [...(prev.steps_log || []), "⛔ Workflow cancelled by user."]
    }));
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      <div className="fade-1" style={{ marginBottom: 28 }}>
        <button onClick={onBack} style={{ background: "none", border: "none", cursor: "pointer", ...bodyText, fontSize: 13, color: C.gold, marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>← Back to Agents</button>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ width: 44, height: 44, borderRadius: 4, background: `${C.inkMid}18`, border: `1px solid ${C.inkMid}33`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>◐</div>
          <div>
            <h1 style={{ ...headingStyle, fontSize: 28 }}>Proposal Draft <em style={{ color: C.inkMid }}>Agent</em></h1>
            <p style={{ ...bodyText, fontSize: 13, marginTop: 2 }}>Orchestrates a team of AI agents to draft a comprehensive research proposal</p>
          </div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 24, marginBottom: 24 }}>
        <div style={{ flex: 1 }}>
          {/* Topic Input */}
          <div className="fade-2" style={{ ...cardBase, padding: "20px 24px", marginBottom: 16 }}>
            <div style={{ ...sectionLabel, marginBottom: 10 }}>Research Topic / Idea *</div>
            <textarea 
              value={topic} 
              onChange={e => setTopic(e.target.value)} 
              placeholder="Describe your research idea, problem statement, or general area of interest..." 
              style={{ width: "100%", minHeight: 100, padding: "12px 14px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: C.creamLight, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14.5, color: C.inkDark, outline: "none", transition: "border-color .2s", resize: "vertical" }} 
              onFocus={e => { e.target.style.borderColor = C.inkMid; }} 
              onBlur={e => { e.target.style.borderColor = C.border; }} 
              disabled={loading}
            />
            <p style={{ ...bodyText, fontSize: 11.5, marginTop: 6 }}>The orchestrator will define boundaries and structure based on this topic.</p>
          </div>

          {/* Paper Selection */}
          <div className="fade-2" style={{ ...cardBase, padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <div style={{ ...sectionLabel }}>Foundation Papers ({selected.size}) *</div>
              <button onClick={() => setSelected(selected.size === papers.length ? new Set() : new Set(papers.map(p => p.id)))} style={{ background: "none", border: "none", cursor: "pointer", ...bodyText, fontSize: 12, color: C.gold, textDecoration: "underline" }} disabled={loading}>
                {selected.size === papers.length ? "Deselect All" : "Select All"}
              </button>
            </div>
            {papers.length === 0 ? (
              <p style={{ ...bodyText, fontSize: 14, textAlign: "center", padding: "20px 0" }}>No indexed papers found.</p>
            ) : (
              <div style={{ maxHeight: 250, overflowY: "auto", paddingRight: 6 }}>
                {papers.map(p => (
                  <label key={p.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 14px", marginBottom: 6, background: selected.has(p.id) ? "rgba(90,62,32,0.06)" : "transparent", border: `1px solid ${selected.has(p.id) ? "rgba(90,62,32,0.3)" : C.border}`, borderRadius: 4, cursor: loading ? "not-allowed" : "pointer", transition: "all .2s", opacity: loading ? 0.7 : 1 }}>
                    <input type="checkbox" checked={selected.has(p.id)} onChange={() => toggle(p.id)} disabled={loading} style={{ accentColor: C.inkMid, width: 16, height: 16 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 13, fontWeight: 700, color: C.inkDark, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{p.title}</div>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Info Sidebar */}
        <div className="fade-2" style={{ width: 260 }}>
          <div style={{ ...cardBase, padding: "20px", background: C.white }}>
            <div style={{ ...sectionLabel, marginBottom: 12 }}>LangGraph Workflow</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {stepsList.map((step, i) => {
                const isActive = liveState.current_step === step.id;
                const isPast = stepsList.findIndex(s => s.id === liveState.current_step) > i;
                
                return (
                  <div key={i} style={{ display: "flex", gap: 10, alignItems: "center", opacity: loading && !isActive && !isPast ? 0.4 : 1, transition: "opacity .3s" }}>
                    <div style={{ width: 18, height: 18, borderRadius: "50%", background: isActive ? C.gold : isPast ? C.green : C.inkDark, color: C.cream, fontSize: 10, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: "bold", boxShadow: isActive ? `0 0 8px ${C.gold}` : "none", transition: "all .3s" }}>
                      {isPast ? "✓" : i + 1}
                    </div>
                    <div>
                      <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 13, fontWeight: isActive ? 800 : 700, color: isActive ? C.gold : C.inkDark, lineHeight: 1 }}>{step.label}</div>
                      <div style={{ ...bodyText, fontSize: 10 }}>{step.agent}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <div className="fade-3" style={{ marginBottom: 32, display: "flex", gap: 12 }}>
        <button onClick={run} disabled={loading || selected.size === 0 || !topic.trim()} style={{ flex: 1, padding: "16px 0", background: loading || selected.size === 0 || !topic.trim() ? C.creamDark : C.inkDark, color: loading || selected.size === 0 || !topic.trim() ? C.inkLight : C.cream, border: "none", borderRadius: 4, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 15, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", cursor: loading || selected.size === 0 || !topic.trim() ? "not-allowed" : "pointer", transition: "all .3s", position: "relative", overflow: "hidden" }}>
          {loading && <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "30%", background: "rgba(255,255,255,0.1)", transform: "skewX(-20deg)", animation: "shimmer 2s infinite linear" }} />}
          {loading ? "⟳ Orchestrating Agents..." : "Start Agentic Workflow"}
        </button>
        {loading && (
          <button onClick={cancel} style={{ padding: "0 24px", background: "rgba(160,82,45,0.12)", color: C.sienna, border: `1.5px solid ${C.sienna}44`, borderRadius: 4, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, fontWeight: 700, cursor: "pointer", transition: "all .2s" }}>
            ✕ Cancel Task
          </button>
        )}
      </div>

      {awaitingQuestionnaire && (
        <div className="fade-1" style={{ marginBottom: 32, padding: 24, background: C.creamLight, border: `1px solid ${C.inkMid}`, borderRadius: 4 }}>
          <div style={{ ...sectionLabel, color: C.inkDark, marginBottom: 12 }}>Agent Questionnaire</div>
          <p style={{ ...bodyText, fontSize: 14, marginBottom: 16 }}>
            The orchestrator needs a bit more context about your existing material to proceed effectively.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 16, marginBottom: 20 }}>
            {questions.map((q: any) => (
              <div key={q.id}>
                <div style={{ ...bodyText, fontSize: 13, fontWeight: "bold", marginBottom: 6 }}>{q.question}</div>
                {q.hint && <div style={{ ...bodyText, fontSize: 11, color: C.inkLight, marginBottom: 6 }}>{q.hint}</div>}
                
                {q.type === "multi_choice" ? (
                  <select 
                    value={answers[q.id] || ""} 
                    onChange={e => setAnswers({ ...answers, [q.id]: e.target.value })}
                    style={{ padding: "8px 12px", border: `1px solid ${C.border}`, borderRadius: 3, background: C.white, width: "100%", maxWidth: 300 }}
                  >
                    <option value="">Select an option...</option>
                    {q.options?.map((opt: string) => <option key={opt} value={opt}>{opt}</option>)}
                  </select>
                ) : q.type === "yes_no" ? (
                  <div style={{ display: "flex", gap: 12 }}>
                    <label style={{ display: "flex", alignItems: "center", gap: 6, ...bodyText, fontSize: 13 }}>
                      <input type="radio" name={q.id} checked={answers[q.id] === "yes"} onChange={() => setAnswers({ ...answers, [q.id]: "yes" })} /> Yes
                    </label>
                    <label style={{ display: "flex", alignItems: "center", gap: 6, ...bodyText, fontSize: 13 }}>
                      <input type="radio" name={q.id} checked={answers[q.id] === "no"} onChange={() => setAnswers({ ...answers, [q.id]: "no" })} /> No
                    </label>
                  </div>
                ) : (
                  <textarea 
                    value={answers[q.id] || ""} 
                    onChange={e => setAnswers({ ...answers, [q.id]: e.target.value })}
                    style={{ padding: "8px 12px", border: `1px solid ${C.border}`, borderRadius: 3, background: C.white, width: "100%", minHeight: 60 }}
                  />
                )}
              </div>
            ))}
          </div>
          <button onClick={submitQuestionnaire} style={{ padding: "12px 24px", background: C.inkDark, color: C.cream, border: "none", borderRadius: 4, cursor: "pointer", fontWeight: "bold" }}>
            Submit Answers & Continue
          </button>
        </div>
      )}

      {awaitingScrapePermission && (
        <div className="fade-1" style={{ marginBottom: 32, padding: 24, background: "rgba(160,82,45,0.08)", border: `1px solid ${C.sienna}44`, borderRadius: 4 }}>
          <div style={{ ...sectionLabel, color: C.sienna, marginBottom: 12 }}>Insufficient Material Detected</div>
          <p style={{ ...bodyText, fontSize: 14, marginBottom: 16 }}>
            The agents determined that your provided papers and answers are not sufficient to draft a complete paper on this topic. 
            Do you grant permission to scrape academic databases (Semantic Scholar, arXiv, OpenAlex) for missing context?
          </p>
          <div style={{ display: "flex", gap: 12 }}>
            <button onClick={() => submitScrapePermission(true)} style={{ padding: "10px 20px", background: C.sienna, color: C.white, border: "none", borderRadius: 4, cursor: "pointer", fontWeight: "bold" }}>
              Yes, Find More Sources
            </button>
            <button onClick={() => submitScrapePermission(false)} style={{ padding: "10px 20px", background: "transparent", color: C.sienna, border: `1px solid ${C.sienna}`, borderRadius: 4, cursor: "pointer", fontWeight: "bold" }}>
              No, Proceed With Existing Material
            </button>
          </div>
        </div>
      )}

      {awaitingApproval && (
        <div className="fade-1" style={{ marginBottom: 32, padding: 24, background: C.creamLight, border: `1px solid ${C.gold}`, borderRadius: 4 }}>
          <div style={{ ...sectionLabel, color: C.inkDark, marginBottom: 12 }}>Human-in-the-Loop: Review Outline & Sources</div>
          <p style={{ ...bodyText, fontSize: 14, marginBottom: 16 }}>
            The agents have generated the research outline and gathered sources. Please review them before heavy drafting begins.
          </p>
          
          <div style={{ display: "flex", gap: 24, marginBottom: 20 }}>
            <div style={{ flex: 1, background: C.white, padding: 16, borderRadius: 4, border: `1px solid ${C.border}`, maxHeight: 300, overflowY: "auto" }}>
              <div style={{ fontWeight: "bold", marginBottom: 12, fontSize: 14 }}>Proposed Outline</div>
              {outline?.sections?.map((sec: any, i: number) => (
                <div key={i} style={{ marginBottom: 12, paddingBottom: 12, borderBottom: i < outline.sections.length - 1 ? `1px solid ${C.border}` : "none" }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{i + 1}. {sec.name}</div>
                  <div style={{ fontSize: 12, color: C.inkLight, marginTop: 4 }}>Needs: {sec.needs}</div>
                  {sec.subsections && <div style={{ fontSize: 12, marginTop: 4 }}>↳ {sec.subsections.join(", ")}</div>}
                </div>
              ))}
            </div>
            
            <div style={{ flex: 1, background: C.white, padding: 16, borderRadius: 4, border: `1px solid ${C.border}`, maxHeight: 300, overflowY: "auto" }}>
              <div style={{ fontWeight: "bold", marginBottom: 12, fontSize: 14 }}>Citation Registry ({sources.length})</div>
              {sources.map((src: any, i: number) => (
                <div key={i} style={{ marginBottom: 10, paddingBottom: 10, borderBottom: i < sources.length - 1 ? `1px solid ${C.border}` : "none", fontSize: 12 }}>
                  <span style={{ fontWeight: 600, color: C.gold }}>[{src.id}]</span> {src.title}
                  <div style={{ color: C.inkLight, marginTop: 2 }}>{src.authors} ({src.year}) • {src.tag}</div>
                </div>
              ))}
            </div>
          </div>
          
          <div style={{ marginBottom: 20 }}>
            <div style={{ ...bodyText, fontSize: 13, fontWeight: "bold", marginBottom: 6 }}>Feedback / Requested Edits (Optional)</div>
            <textarea 
              value={approvalComment} 
              onChange={e => setApprovalComment(e.target.value)}
              placeholder="E.g., Please merge the literature review with the background section, and focus more on the second theme..." 
              style={{ width: "100%", padding: "10px 12px", border: `1px solid ${C.border}`, borderRadius: 3, minHeight: 70 }}
            />
          </div>

          <button onClick={approve} style={{ padding: "12px 24px", background: C.gold, color: C.white, border: "none", borderRadius: 4, cursor: "pointer", fontWeight: "bold" }}>
            Approve & Start Drafting
          </button>
        </div>
      )}

      {(loading || result) && !result?.error && !awaitingApproval && !awaitingQuestionnaire && !awaitingScrapePermission && (
        <div className="fade-1" style={{ marginBottom: 40 }}>
          <div style={{ display: "flex", gap: 8, marginBottom: -1 }}>
            <button onClick={() => setActiveTab("proposal")} disabled={!result} style={{ padding: "10px 20px", background: activeTab === "proposal" ? C.white : "transparent", border: `1px solid ${C.border}`, borderBottomColor: activeTab === "proposal" ? C.white : C.border, borderRadius: "4px 4px 0 0", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, fontWeight: activeTab === "proposal" ? 600 : 400, color: activeTab === "proposal" ? C.inkDark : C.inkLight, cursor: !result ? "not-allowed" : "pointer", position: "relative", zIndex: activeTab === "proposal" ? 1 : 0, opacity: !result ? 0.5 : 1 }}>
              Final Proposal
            </button>
            <button onClick={() => setActiveTab("analysis")} disabled={!result} style={{ padding: "10px 20px", background: activeTab === "analysis" ? C.white : "transparent", border: `1px solid ${C.border}`, borderBottomColor: activeTab === "analysis" ? C.white : C.border, borderRadius: "4px 4px 0 0", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, fontWeight: activeTab === "analysis" ? 600 : 400, color: activeTab === "analysis" ? C.inkDark : C.inkLight, cursor: !result ? "not-allowed" : "pointer", position: "relative", zIndex: activeTab === "analysis" ? 1 : 0, opacity: !result ? 0.5 : 1 }}>
              Agent Analysis
            </button>
            <button onClick={() => setActiveTab("logs")} style={{ padding: "10px 20px", background: activeTab === "logs" ? C.white : "transparent", border: `1px solid ${C.border}`, borderBottomColor: activeTab === "logs" ? C.white : C.border, borderRadius: "4px 4px 0 0", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, fontWeight: activeTab === "logs" ? 600 : 400, color: activeTab === "logs" ? C.inkDark : C.inkLight, cursor: "pointer", position: "relative", zIndex: activeTab === "logs" ? 1 : 0 }}>
              Workflow Execution Logs
              {loading && <span style={{ marginLeft: 6, display: "inline-block", animation: "spin 1s linear infinite" }}>⟳</span>}
            </button>
          </div>
          
          <div style={{ ...cardBase, background: C.white, borderRadius: "0 4px 4px 4px", padding: "40px", minHeight: 400 }}>
            {activeTab === "proposal" && result && (
              <div>
                <div style={{ ...sectionLabel, color: C.inkDark, marginBottom: 16 }}>Pipeline Completed Successfully!</div>
                <p style={{ ...bodyText, fontSize: 15, marginBottom: 20 }}>Your research paper and completion guide have been generated. You can download the dynamic PDFs below.</p>
                <div style={{ display: "flex", gap: 16 }}>
                  <a href={`${API}/reports/${sessionId}/draft.pdf`} target="_blank" rel="noreferrer" style={{ padding: "14px 20px", background: C.inkDark, color: C.cream, borderRadius: 4, textDecoration: "none", fontWeight: 600, fontSize: 14, display: "inline-block" }}>
                    📄 Download Research Draft (PDF)
                  </a>
                  <a href={`${API}/reports/${sessionId}/guide.pdf`} target="_blank" rel="noreferrer" style={{ padding: "14px 20px", background: C.gold, color: C.white, borderRadius: 4, textDecoration: "none", fontWeight: 600, fontSize: 14, display: "inline-block" }}>
                    📋 Download Completion Guide (PDF)
                  </a>
                </div>
              </div>
            )}
            
            {activeTab === "analysis" && result && (
              <div>
                <div style={{ ...sectionLabel, marginBottom: 12 }}>Agent Analysis Unavailable</div>
                <div style={{ padding: 16, background: C.creamLight, border: `1px solid ${C.border}`, borderRadius: 4, marginBottom: 24, ...bodyText, fontSize: 13.5, whiteSpace: "pre-wrap" }}>The backend now generates `.docx` files instead of raw text. Please check the generated files for your full research paper and gap analysis completion guide!</div>
              </div>
            )}
            
            {activeTab === "logs" && (
              <div>
                <div style={{ ...sectionLabel, marginBottom: 16 }}>LangGraph Orchestration Trace</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {liveState.steps_log?.map((log: string, i: number) => (
                    <div key={i} className="fade-1" style={{ display: "flex", alignItems: "flex-start", gap: 12, padding: "10px 14px", background: C.creamLight, borderRadius: 4, border: `1px solid ${C.border}` }}>
                      <div style={{ color: log.startsWith("✓") ? C.green : C.gold, marginTop: 1, fontSize: 16 }}>{log.startsWith("✓") ? "✓" : "⚡"}</div>
                      <div style={{ ...bodyText, fontSize: 14 }}>{log.replace("✓ ", "").replace("⚡ ", "")}</div>
                    </div>
                  ))}
                  {loading && (
                    <div className="fade-1" style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 14px" }}>
                      <div style={{ color: C.gold, animation: "spin 1s linear infinite" }}>⟳</div>
                      <div style={{ ...bodyText, fontSize: 14, color: C.inkLight }}>Agent is working...</div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {result?.error && (
        <div style={{ ...cardBase, padding: "20px", borderColor: "rgba(160,82,45,0.3)", background: "rgba(160,82,45,0.05)", marginTop: 24 }}>
          <span style={{ ...bodyText, color: C.sienna }}>⚠ Workflow failed: {result.error}</span>
        </div>
      )}

      <style>{`
        .proposal-markdown h1 { font-family: 'Playfair Display', serif; font-size: 26px; color: ${C.inkDark}; margin-top: 0; margin-bottom: 24px; text-align: center; }
        .proposal-markdown h2 { font-family: 'Playfair Display', serif; font-size: 20px; color: ${C.inkDark}; margin-top: 32px; margin-bottom: 16px; border-bottom: 1px solid ${C.border}; padding-bottom: 8px; }
        .proposal-markdown h3 { font-family: 'Playfair Display', serif; font-size: 16px; color: ${C.inkDark}; margin-top: 24px; margin-bottom: 12px; }
        .proposal-markdown ul, .proposal-markdown ol { padding-left: 24px; margin-bottom: 16px; }
        .proposal-markdown li { margin-bottom: 8px; }
        @keyframes shimmer { 0% { transform: skewX(-20deg) translateX(-150%); } 100% { transform: skewX(-20deg) translateX(300%); } }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

