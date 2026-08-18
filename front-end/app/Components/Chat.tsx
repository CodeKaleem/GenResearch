"use client";
import { useState, useEffect, useRef } from "react";
import { getCurrentUserId } from "../../lib/db";

const C = {
  cream: "#f5f0e8", creamLight: "#faf8f2", creamDark: "#efe8d8",
  inkDark: "#2c1f0e", inkMid: "#5a3e20", inkLight: "#7a6040",
  gold: "#8b6914", goldLight: "#c8971e", goldFaint: "rgba(139,105,20,0.09)",
  sienna: "#a0522d", umber: "#6b5c38", white: "#fffef9",
  border: "rgba(180,160,120,0.22)", green: "#5a8a3c",
  shadow: "rgba(120,100,60,0.10)",
  borderGold: "rgba(139,105,20,0.4)",
};

const API_BASE = "http://localhost:8000";

export interface Source {
  paper_id: string;
  title: string;
  relevance: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  timestamp: string;
  isStreaming?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

interface PaperOption {
  id: string;
  title: string;
  status: string;
}

export default function Chat() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [papers, setPapers] = useState<PaperOption[]>([]);
  const [selectedPaper, setSelectedPaper] = useState<string>("all");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load user & sessions from localStorage
  useEffect(() => {
    const init = async () => {
      const uid = await getCurrentUserId();
      setUserId(uid);
      if (uid) {
        const storageKey = `genresearch_chat_sessions_${uid}`;
        try {
          const saved = localStorage.getItem(storageKey);
          let loadedSessions: ChatSession[] = [];
          if (saved) {
            loadedSessions = JSON.parse(saved);
          } else {
            // Check legacy storage
            const legacySaved = localStorage.getItem(`genresearch_chat_${uid}`);
            if (legacySaved) {
              const legacyMsgs = JSON.parse(legacySaved);
              if (legacyMsgs.length > 0) {
                const firstUserMsg = legacyMsgs.find((m: any) => m.role === "user")?.content || "Previous Research";
                const title = firstUserMsg.slice(0, 30) + (firstUserMsg.length > 30 ? "..." : "");
                loadedSessions = [{
                  id: crypto.randomUUID(),
                  title,
                  createdAt: new Date().toISOString(),
                  updatedAt: new Date().toISOString(),
                  messages: legacyMsgs,
                }];
              }
            }
          }

          if (loadedSessions.length === 0) {
            const newS: ChatSession = {
              id: crypto.randomUUID(),
              title: "New Conversation",
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              messages: [],
            };
            loadedSessions = [newS];
          }

          setSessions(loadedSessions);
          setActiveSessionId(loadedSessions[0].id);
        } catch (e) {
          console.error("Failed to load chat sessions", e);
        }

        try {
          const res = await fetch(`${API_BASE}/papers/?user_id=${uid}`);
          const data = await res.json();
          setPapers(
            (data.papers || [])
              .filter((p: PaperOption) => p.status === "indexed")
              .map((p: PaperOption) => ({ id: p.id, title: p.title, status: p.status }))
          );
        } catch {
          /* papers optional */
        }
      }
    };
    init();
  }, []);

  // Save sessions to localStorage whenever they change
  useEffect(() => {
    if (userId && sessions.length > 0) {
      try {
        localStorage.setItem(`genresearch_chat_sessions_${userId}`, JSON.stringify(sessions));
      } catch {
        /* storage limit */
      }
    }
  }, [sessions, userId]);

  // Current active session
  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0];
  const activeMessages = activeSession ? activeSession.messages : [];

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [activeMessages]);

  const handleCreateNewChat = () => {
    // If an uninitiated empty chat already exists, switch to it instead of creating duplicates
    const existingEmpty = sessions.find((s) => s.messages.length === 0 || s.title === "New Conversation");
    if (existingEmpty) {
      setActiveSessionId(existingEmpty.id);
      setInput("");
      setTimeout(() => inputRef.current?.focus(), 100);
      return;
    }

    const newS: ChatSession = {
      id: crypto.randomUUID(),
      title: "New Conversation",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [],
    };
    setSessions((prev) => [newS, ...prev]);
    setActiveSessionId(newS.id);
    setInput("");
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = sessions.filter((s) => s.id !== sessionId);
    if (updated.length === 0) {
      const fresh: ChatSession = {
        id: crypto.randomUUID(),
        title: "New Conversation",
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [],
      };
      setSessions([fresh]);
      setActiveSessionId(fresh.id);
    } else {
      setSessions(updated);
      if (activeSessionId === sessionId) {
        setActiveSessionId(updated[0].id);
      }
    }
  };

  const sendMessage = async () => {
    const query = input.trim();
    if (!query || !userId || !activeSession || isLoading) return;

    // Auto-update session title if it's the first message
    let sessionTitle = activeSession.title;
    if (activeSession.messages.length === 0 || activeSession.title === "New Conversation") {
      sessionTitle = query.slice(0, 32) + (query.length > 32 ? "..." : "");
    }

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: query,
      timestamp: new Date().toISOString(),
    };

    const assistantId = crypto.randomUUID();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      sources: [],
      timestamp: new Date().toISOString(),
      isStreaming: true,
    };

    // Update active session messages
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === activeSession.id) {
          return {
            ...s,
            title: sessionTitle,
            updatedAt: new Date().toISOString(),
            messages: [...s.messages, userMsg, assistantMsg],
          };
        }
        return s;
      })
    );

    setInput("");
    setIsLoading(true);

    try {
      const body: Record<string, unknown> = {
        user_id: userId,
        query,
        top_k: 5,
      };
      if (selectedPaper !== "all") {
        body.paper_id = selectedPaper;
      }

      const res = await fetch(`${API_BASE}/chat/ask-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let fullContent = "";
      let sources: Source[] = [];

      if (reader) {
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
              if (data.type === "sources") {
                sources = data.sources || [];
              } else if (data.type === "token") {
                fullContent += data.content;
                setSessions((prev) =>
                  prev.map((s) => {
                    if (s.id === activeSession.id) {
                      return {
                        ...s,
                        messages: s.messages.map((m) =>
                          m.id === assistantId ? { ...m, content: fullContent, sources } : m
                        ),
                      };
                    }
                    return s;
                  })
                );
              } else if (data.type === "answer") {
                fullContent = data.content;
              }
            } catch {
              /* ignore stream parse error */
            }
          }
        }
      }

      // Final update to clear streaming state
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === activeSession.id) {
            return {
              ...s,
              messages: s.messages.map((m) =>
                m.id === assistantId
                  ? { ...m, content: fullContent || "No response received.", sources, isStreaming: false }
                  : m
              ),
            };
          }
          return s;
        })
      );
    } catch (err) {
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === activeSession.id) {
            return {
              ...s,
              messages: s.messages.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      content: `Error: ${err instanceof Error ? err.message : "Failed to connect to backend."}`,
                      isStreaming: false,
                    }
                  : m
              ),
            };
          }
          return s;
        })
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearCurrentChat = () => {
    if (!activeSession) return;
    setSessions((prev) =>
      prev.map((s) => (s.id === activeSession.id ? { ...s, messages: [] } : s))
    );
  };

  return (
    <div style={{ display: "flex", gap: 24, height: "calc(100vh - 120px)", maxWidth: 1180, margin: "0 auto" }}>
      
      {/* ── Main Chat Area (LEFT SIDE) ────────────────────────── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        
        {/* Header */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.gold, textTransform: "uppercase", letterSpacing: "0.15em" }}>
                  AI Research Assistant
                </span>
              </div>
              <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 24, fontWeight: 900, color: C.inkDark, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {activeSession?.title || "Ask Your Documents"}
              </h2>
            </div>
            {activeMessages.length > 0 && (
              <button
                onClick={clearCurrentChat}
                style={{
                  background: "transparent",
                  border: `1.5px solid ${C.border}`,
                  borderRadius: 3,
                  padding: "6px 12px",
                  fontFamily: "'Crimson Pro', Georgia, serif",
                  fontSize: 12,
                  color: C.inkLight,
                  cursor: "pointer",
                  transition: "all .2s",
                }}
                onMouseEnter={(e) => {
                  (e.target as HTMLButtonElement).style.borderColor = C.sienna;
                  (e.target as HTMLButtonElement).style.color = C.sienna;
                }}
                onMouseLeave={(e) => {
                  (e.target as HTMLButtonElement).style.borderColor = C.border;
                  (e.target as HTMLButtonElement).style.color = C.inkLight;
                }}
              >
                Clear Current Thread
              </button>
            )}
          </div>
        </div>

        {/* Paper Filter Scope */}
        {papers.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11.5, fontWeight: 600, color: C.gold, textTransform: "uppercase", letterSpacing: "0.1em" }}>
                Search Scope
              </span>
              <select
                value={selectedPaper}
                onChange={(e) => setSelectedPaper(e.target.value)}
                style={{
                  flex: 1,
                  maxWidth: 360,
                  padding: "6px 10px",
                  fontFamily: "'Crimson Pro', Georgia, serif",
                  fontSize: 13,
                  color: C.inkDark,
                  background: C.creamLight,
                  border: `1px solid ${C.border}`,
                  borderRadius: 3,
                  cursor: "pointer",
                  outline: "none",
                }}
              >
                <option value="all">All Documents ({papers.length})</option>
                {papers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {/* Messages Scroll Area */}
        <div
          ref={scrollRef}
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "16px 4px",
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}
        >
          {activeMessages.length === 0 && (
            <div
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                padding: 30,
              }}
            >
              <div
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: "50%",
                  background: C.goldFaint,
                  border: `1.5px solid ${C.borderGold}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 24,
                  marginBottom: 16,
                }}
              >
                💬
              </div>
              <h3 style={{ fontFamily: "'Playfair Display', serif", fontSize: 20, fontWeight: 800, color: C.inkDark, marginBottom: 6 }}>
                New Chat Thread
              </h3>
              <p style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14.5, color: C.inkLight, maxWidth: 400, lineHeight: 1.5 }}>
                Ask a research question about your indexed papers to begin a new discussion thread.
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 20, justifyContent: "center" }}>
                {[
                  "Summarize key findings",
                  "What methodology was used?",
                  "What are the main conclusions?",
                  "Compare results across papers",
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => {
                      setInput(suggestion);
                      inputRef.current?.focus();
                    }}
                    style={{
                      padding: "7px 14px",
                      background: C.creamLight,
                      border: `1px solid ${C.border}`,
                      borderRadius: 18,
                      fontFamily: "'Crimson Pro', Georgia, serif",
                      fontSize: 12.5,
                      color: C.inkMid,
                      cursor: "pointer",
                      transition: "all .2s",
                    }}
                    onMouseEnter={(e) => {
                      (e.target as HTMLButtonElement).style.borderColor = C.gold;
                      (e.target as HTMLButtonElement).style.color = C.gold;
                      (e.target as HTMLButtonElement).style.background = C.goldFaint;
                    }}
                    onMouseLeave={(e) => {
                      (e.target as HTMLButtonElement).style.borderColor = C.border;
                      (e.target as HTMLButtonElement).style.color = C.inkMid;
                      (e.target as HTMLButtonElement).style.background = C.creamLight;
                    }}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {activeMessages.map((msg) => (
            <div
              key={msg.id}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: msg.role === "user" ? "flex-end" : "flex-start",
              }}
            >
              {/* Role Label */}
              <span
                style={{
                  fontFamily: "'Crimson Pro', Georgia, serif",
                  fontSize: 10,
                  fontWeight: 600,
                  color: msg.role === "user" ? C.gold : C.green,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  marginBottom: 4,
                }}
              >
                {msg.role === "user" ? "You" : "GenResearch AI"}
              </span>

              {/* Message Bubble */}
              <div
                style={{
                  maxWidth: msg.role === "user" ? "75%" : "88%",
                  padding: "12px 16px",
                  background: msg.role === "user" ? C.inkDark : C.creamLight,
                  color: msg.role === "user" ? C.cream : C.inkDark,
                  border: `1px solid ${msg.role === "user" ? "transparent" : C.border}`,
                  borderRadius: msg.role === "user" ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
                  fontFamily: "'Crimson Pro', Georgia, serif",
                  fontSize: 14,
                  lineHeight: 1.6,
                  boxShadow: `0 2px 8px ${C.shadow}`,
                }}
              >
                {msg.content || (msg.isStreaming && (
                  <div style={{ display: "flex", alignItems: "center", gap: 8, color: C.inkLight }}>
                    <span style={{ display: "inline-block", animation: "spin 1.2s linear infinite" }}>⟳</span>
                    Searching documents and generating answer...
                  </div>
                ))}
              </div>

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && !msg.isStreaming && (
                <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {msg.sources.map((src, i) => (
                    <div
                      key={`${src.paper_id}-${i}`}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        padding: "4px 10px",
                        background: C.goldFaint,
                        border: `1px solid ${C.borderGold}`,
                        borderRadius: 16,
                        fontFamily: "'Crimson Pro', Georgia, serif",
                        fontSize: 11,
                      }}
                    >
                      <span style={{ color: C.gold, fontWeight: 700 }}>📄</span>
                      <span style={{ color: C.inkMid, maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {src.title}
                      </span>
                      <span
                        style={{
                          fontSize: 9.5,
                          color: C.green,
                          fontWeight: 600,
                          background: "rgba(90,138,60,0.1)",
                          padding: "1px 5px",
                          borderRadius: 6,
                        }}
                      >
                        {Math.round(src.relevance * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Timestamp */}
              <span
                style={{
                  fontFamily: "'Crimson Pro', Georgia, serif",
                  fontSize: 10,
                  color: C.inkLight,
                  marginTop: 3,
                  opacity: 0.6,
                }}
              >
                {new Date(msg.timestamp).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true })}
              </span>
            </div>
          ))}
        </div>

        {/* Input Box */}
        <div style={{ padding: "12px 0 0", borderTop: `1px solid ${C.border}` }}>
          <div
            style={{
              display: "flex",
              gap: 10,
              alignItems: "flex-end",
              background: C.creamLight,
              border: `1.5px solid ${C.border}`,
              borderRadius: 6,
              padding: "8px 12px",
            }}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your documents..."
              rows={1}
              style={{
                flex: 1,
                resize: "none",
                border: "none",
                outline: "none",
                background: "transparent",
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 14,
                color: C.inkDark,
                lineHeight: 1.4,
                maxHeight: 100,
                overflowY: "auto",
              }}
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              style={{
                width: 34,
                height: 34,
                borderRadius: "50%",
                flexShrink: 0,
                background: input.trim() && !isLoading ? C.inkDark : C.creamDark,
                border: "none",
                cursor: input.trim() && !isLoading ? "pointer" : "not-allowed",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: input.trim() && !isLoading ? C.cream : C.inkLight,
                fontSize: 14,
                transition: "all .2s",
              }}
            >
              {isLoading ? "⟳" : "➤"}
            </button>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 4px 0", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10.5, color: C.inkLight, opacity: 0.6 }}>
            <span>Press Enter to send · Shift+Enter for new line</span>
            <span>Mistral 7B + nomic-embed-text</span>
          </div>
        </div>

      </div>

      {/* ── Chat Threads Sidebar (RIGHT SIDE) ─────────────────── */}
      <div
        style={{
          width: 260,
          background: C.creamLight,
          border: `1px solid ${C.border}`,
          borderRadius: 6,
          padding: "16px 12px",
          display: "flex",
          flexDirection: "column",
          flexShrink: 0,
        }}
      >
        {/* New Chat Button */}
        <button
          onClick={handleCreateNewChat}
          style={{
            width: "100%",
            padding: "11px 14px",
            borderRadius: 4,
            background: C.inkDark,
            color: C.cream,
            border: "none",
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            marginBottom: 16,
            transition: "all .2s",
            boxShadow: `0 2px 8px ${C.shadow}`,
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = C.gold; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = C.inkDark; }}
        >
          <span>+</span> New Chat
        </button>

        {/* Sessions Header */}
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 700, color: C.gold, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 10, paddingLeft: 4 }}>
          Chat History ({sessions.length})
        </div>

        {/* List of Conversations */}
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 4, paddingRight: 2 }}>
          {sessions.map((s) => {
            const isActive = s.id === activeSessionId;
            return (
              <div
                key={s.id}
                onClick={() => setActiveSessionId(s.id)}
                style={{
                  padding: "9px 12px",
                  borderRadius: 4,
                  background: isActive ? C.white : "transparent",
                  border: `1px solid ${isActive ? C.borderGold : "transparent"}`,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  transition: "all .2s",
                  boxShadow: isActive ? `0 2px 6px ${C.shadow}` : "none",
                }}
                onMouseEnter={(e) => {
                  if (!isActive) (e.currentTarget as HTMLDivElement).style.background = "rgba(139,105,20,0.06)";
                }}
                onMouseLeave={(e) => {
                  if (!isActive) (e.currentTarget as HTMLDivElement).style.background = "transparent";
                }}
              >
                <div style={{ flex: 1, minWidth: 0, paddingRight: 6 }}>
                  <div
                    style={{
                      fontFamily: "'Playfair Display', serif",
                      fontSize: 13,
                      fontWeight: isActive ? 800 : 600,
                      color: isActive ? C.inkDark : C.inkMid,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    💬 {s.title}
                  </div>
                  <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10.5, color: C.inkLight, opacity: 0.8, marginTop: 2 }}>
                    {new Date(s.updatedAt).toLocaleDateString("en-US", { month: "short", day: "numeric" })} · {s.messages.length} msgs
                  </div>
                </div>

                <button
                  onClick={(e) => handleDeleteSession(s.id, e)}
                  title="Delete Chat"
                  style={{
                    background: "none",
                    border: "none",
                    color: C.inkLight,
                    fontSize: 12,
                    cursor: "pointer",
                    padding: "2px 4px",
                    opacity: 0.6,
                    transition: "opacity .2s, color .2s",
                  }}
                  onMouseEnter={(e) => {
                    (e.target as HTMLButtonElement).style.opacity = "1";
                    (e.target as HTMLButtonElement).style.color = C.sienna;
                  }}
                  onMouseLeave={(e) => {
                    (e.target as HTMLButtonElement).style.opacity = "0.6";
                    (e.target as HTMLButtonElement).style.color = C.inkLight;
                  }}
                >
                  ✕
                </button>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
