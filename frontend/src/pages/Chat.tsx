/**
 * Chat page — AI Tutor Chat (AITutorChat.jsx design).
 * Integrated with backend /api/chat (Ollama + RAG), getUserStats, updateUserStats.
 */

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import {
  getUserStats,
  updateUserStats,
  postChat,
  getTextbooks,
  uploadTextbook,
  ragSearch,
  type ChatMessage,
} from "../services/api";

const MAX_HISTORY = 50;
const LEVELS = ["Beginner", "Intermediate", "Advanced"] as const;

const QUICK_ACTIONS = [
  { label: "Explain Topic", prompt: "Explain this concept: " },
  { label: "Quiz Me", prompt: "Quiz me on: " },
  { label: "Flashcards", prompt: "Create flashcards for: " },
  { label: "Step-by-Step", prompt: "Explain step-by-step: " },
];

const QUICK_CHIPS = [
  "Explain this concept",
  "Give me practice questions",
  "Summarise chapter",
  "Check my answer",
];

const SUBJECTS = ["General", "Maths", "Science", "Computer Science", "Biology", "Chem", "Physics"] as const;

const SUBJECT_COLORS: Record<string, string> = {
  Physics: "#FA5C5C",
  Biology: "#10b981",
  Maths: "#00a8e8",
  Science: "#FD8A6B",
  "Computer Science": "#FEC288",
  Chem: "#8b5cf6",
  General: "#9ca3af",
};

function formatHistoryTime(iso: string): "Today" | "Yesterday" | "Earlier" {
  try {
    const d = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const days = Math.floor(diff / (24 * 60 * 60 * 1000));
    if (days === 0) return "Today";
    if (days === 1) return "Yesterday";
    return "Earlier";
  } catch {
    return "Earlier";
  }
}

/** Build sidebar history items from flat chat_history */
function buildHistoryItems(messages: ChatMessage[]): Array<{
  id: string;
  title: string;
  preview: string;
  subject: string;
  time: "Today" | "Yesterday" | "Earlier";
  startIdx: number;
}> {
  const items: Array<{
    id: string;
    title: string;
    preview: string;
    subject: string;
    time: "Today" | "Yesterday" | "Earlier";
    startIdx: number;
  }> = [];
  for (let i = 0; i < messages.length; i++) {
    if (messages[i].role === "user") {
      const content = messages[i].content;
      const title = content.length > 40 ? content.slice(0, 37) + "..." : content;
      const preview = content.length > 50 ? content.slice(0, 47) + "..." : content;
      items.push({
        id: `hist-${i}`,
        title,
        preview,
        subject: "General",
        time: formatHistoryTime(messages[i].timestamp),
        startIdx: i,
      });
    }
  }
  return items.reverse().slice(0, 20);
}

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    role: "assistant",
    content:
      "Hi! I'm your AI tutor powered by Llama 3.2 with RAG grounding from your textbooks. Ask me anything — I work fully offline. 🎓",
    timestamp: new Date().toISOString(),
  },
];

export function ChatPage() {
  const { profile, connectivityStatus } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [level, setLevel] = useState<string>("Beginner");
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [clarifyInputs, setClarifyInputs] = useState<Record<number, string>>({});
  const [clarifyExpanded, setClarifyExpanded] = useState<Record<number, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [subject, setSubject] = useState<string>("General");
  const [activeTextbook, setActiveTextbook] = useState<string | null>(null);
  const [textbooks, setTextbooks] = useState<{ id: string; name: string }[]>([]);
  const [attachOpen, setAttachOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [subjectOpen, setSubjectOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<{ content: string; source?: string; subject?: string }[]>([]);
  const [searching, setSearching] = useState(false);
  const [uploading, setUploading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const attachRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLDivElement>(null);
  const subjectRef = useRef<HTMLDivElement>(null);
  const attachDropdownRef = useRef<HTMLDivElement>(null);
  const searchDropdownRef = useRef<HTMLDivElement>(null);
  const subjectDropdownRef = useRef<HTMLDivElement>(null);

  type DropdownPos = { top: number; left: number; width: number; bottom: number };
  const [attachPos, setAttachPos] = useState<DropdownPos | null>(null);
  const [searchPos, setSearchPos] = useState<DropdownPos | null>(null);
  const [subjectPos, setSubjectPos] = useState<DropdownPos | null>(null);

  /** Open upward when more space above; else open downward. Constrain to viewport so dropdown stays visible. */
  const getDropdownPlacement = useCallback((pos: DropdownPos) => {
    if (typeof window === "undefined") {
      return { top: pos.top - 4, transform: "translateY(-100%)" as const, maxHeight: 320 };
    }
    const spaceAbove = pos.top;
    const spaceBelow = window.innerHeight - pos.bottom;
    const openUp = spaceAbove >= spaceBelow;
    const gap = 8;
    const maxHeight = openUp
      ? Math.max(120, spaceAbove - gap)
      : Math.max(120, spaceBelow - gap);
    return openUp
      ? { top: pos.top - 4, transform: "translateY(-100%)" as const, maxHeight }
      : { top: pos.bottom + 4, maxHeight };
  }, []);

  const updatePositions = useCallback(() => {
    if (attachOpen && attachRef.current) {
      const r = attachRef.current.getBoundingClientRect();
      setAttachPos({ top: r.top, left: r.left, width: r.width, bottom: r.bottom });
    } else {
      setAttachPos(null);
    }
    if (searchOpen && searchRef.current) {
      const r = searchRef.current.getBoundingClientRect();
      setSearchPos({ top: r.top, left: r.left, width: r.width, bottom: r.bottom });
    } else {
      setSearchPos(null);
    }
    if (subjectOpen && subjectRef.current) {
      const r = subjectRef.current.getBoundingClientRect();
      setSubjectPos({ top: r.top, left: r.left, width: r.width, bottom: r.bottom });
    } else {
      setSubjectPos(null);
    }
  }, [attachOpen, searchOpen, subjectOpen]);

  useLayoutEffect(() => {
    updatePositions();
  }, [updatePositions]);

  useEffect(() => {
    if (!attachOpen && !searchOpen && !subjectOpen) return;
    const onScrollOrResize = () => updatePositions();
    window.addEventListener("scroll", onScrollOrResize, true);
    window.addEventListener("resize", onScrollOrResize);
    const main = document.querySelector("main");
    if (main) main.addEventListener("scroll", onScrollOrResize);
    return () => {
      window.removeEventListener("scroll", onScrollOrResize, true);
      window.removeEventListener("resize", onScrollOrResize);
      main?.removeEventListener("scroll", onScrollOrResize);
    };
  }, [attachOpen, searchOpen, subjectOpen, updatePositions]);

  const loadInitial = useCallback(async () => {
    try {
      const stats = await getUserStats();
      const hist = stats.chat_history;
      if (Array.isArray(hist) && hist.length > 0) {
        setMessages(hist.slice(-MAX_HISTORY));
      } else {
        setMessages(INITIAL_MESSAGES);
      }
      const diff = stats.preferences?.difficulty_level;
      if (diff && LEVELS.includes(diff as (typeof LEVELS)[number])) {
        setLevel(diff);
      }
    } catch {
      setMessages(INITIAL_MESSAGES);
    }
  }, []);

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  useEffect(() => {
    getTextbooks().then((r) => setTextbooks(r.textbooks)).catch(() => setTextbooks([]));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const saveHistory = useCallback(async (next: ChatMessage[]) => {
    setMessages(next);
    try {
      await updateUserStats({ chat_history: next.slice(-MAX_HISTORY) });
    } catch {
      // ignore
    }
  }, []);

  const sendMessage = useCallback(
    async (text: string, isClarification = false) => {
      if (!text.trim()) return;
      setError(null);
      const userMsg: ChatMessage = {
        role: "user",
        content: text.trim(),
        timestamp: new Date().toISOString(),
        is_clarification: isClarification,
      };
      const isFirstMessage = messages.length === 1 && messages[0].role === "assistant";
      const next = isFirstMessage ? [userMsg] : [...messages, userMsg];
      await saveHistory(next);
      setLoading(true);
      try {
        const res = await postChat({
          message: text.trim(),
          is_clarification: isClarification,
          context: {
            difficulty: level,
            chat_history: next.slice(-20).map((m) => ({ role: m.role, content: m.content })),
            subject: subject !== "General" ? subject : undefined,
            active_textbook: activeTextbook ?? undefined,
            user_id: profile.profile_name ?? null,
          },
        });
        const assistantMsg: ChatMessage = {
          role: "assistant",
          content: res.text,
          timestamp: new Date().toISOString(),
          is_clarification: isClarification,
        };
        await saveHistory([...next, assistantMsg]);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to get response.");
        const fallback: ChatMessage = {
          role: "assistant",
          content:
            "I couldn't complete that request. Please check that Ollama is running and try again.",
          timestamp: new Date().toISOString(),
          is_clarification: isClarification,
        };
        await saveHistory([...next, fallback]);
      } finally {
        setLoading(false);
      }
    },
    [messages, level, subject, activeTextbook, profile.profile_name, saveHistory]
  );

  useEffect(() => {
    getTextbooks().then((r) => setTextbooks(r.textbooks)).catch(() => setTextbooks([]));
  }, [attachOpen]);

  const handleTextbookUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) return;
    setUploading(true);
    try {
      const res = await uploadTextbook(file);
      setTextbooks((p) => [...p, { id: res.id, name: res.name }]);
      setActiveTextbook(res.id);
      setAttachOpen(false);
    } catch {
      setError("Upload failed. Try again.");
    } finally {
      setUploading(false);
    }
    e.target.value = "";
  }, []);

  const handleRagSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await ragSearch(searchQuery.trim(), 5);
      setSearchResults(res.results ?? []);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }, [searchQuery]);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      const target = e.target as Node;
      const insideAny =
        attachRef.current?.contains(target) ||
        searchRef.current?.contains(target) ||
        subjectRef.current?.contains(target) ||
        attachDropdownRef.current?.contains(target) ||
        searchDropdownRef.current?.contains(target) ||
        subjectDropdownRef.current?.contains(target);
      if (!insideAny) {
        setAttachOpen(false);
        setSearchOpen(false);
        setSubjectOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const handleNewChat = useCallback(async () => {
    setMessages(INITIAL_MESSAGES);
    setActiveChatId(null);
    setClarifyInputs({});
    setClarifyExpanded({});
    setError(null);
    try {
      await updateUserStats({ chat_history: [] });
    } catch {
      // ignore
    }
  }, []);

  const handleClear = useCallback(async () => {
    setMessages(INITIAL_MESSAGES);
    setActiveChatId(null);
    setClarifyInputs({});
    setClarifyExpanded({});
    setError(null);
    try {
      await updateUserStats({ chat_history: [] });
    } catch {
      // ignore
    }
  }, []);

  const handleLevelChange = useCallback((newLevel: string) => {
    setLevel(newLevel);
    updateUserStats({ preferences: { difficulty_level: newLevel } }).catch(() => {});
  }, []);

  const handleClarify = useCallback(
    (idx: number) => {
      const val = clarifyInputs[idx]?.trim();
      if (!val) return;
      setClarifyInputs((p) => ({ ...p, [idx]: "" }));
      setClarifyExpanded((p) => ({ ...p, [idx]: false }));
      sendMessage(`[Clarification] ${val}`, true);
    },
    [clarifyInputs, sendMessage]
  );

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    sendMessage(text, false);
  }, [input, loading, sendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const displayMessages = useMemo(() => {
    if (messages.length === 1 && messages[0].role === "assistant") return messages;
    return messages.filter((m) => m.role === "user" || m.role === "assistant");
  }, [messages]);

  const historyItems = useMemo(() => buildHistoryItems(messages), [messages]);

  const groupedHistory = useMemo(() => {
    const groups: Record<"Today" | "Yesterday" | "Earlier", typeof historyItems> = {
      Today: [],
      Yesterday: [],
      Earlier: [],
    };
    for (const item of historyItems) {
      groups[item.time].push(item);
    }
    return groups;
  }, [historyItems]);

  const isOnline = connectivityStatus === "online";

  return (
    <div
      className="flex -m-6 min-h-0 flex-1 overflow-visible"
      style={{
        background: "#f0f4ff",
        fontFamily: "'Plus Jakarta Sans', 'DM Sans', sans-serif",
      }}
    >
      <style>{`
        .chat-hist-item { transition: background 0.18s, transform 0.15s; cursor: pointer; }
        .chat-hist-item:hover { background: rgba(0,168,232,0.07) !important; transform: translateX(3px); }
        .chat-hist-item.active { background: rgba(0,168,232,0.12) !important; border-left: 3px solid #00a8e8 !important; }
        .chat-action-btn { transition: all 0.18s ease; cursor: pointer; }
        .chat-action-btn:hover { transform: translateY(-2px); }
        .chat-send-btn { transition: all 0.18s ease; cursor: pointer; }
        .chat-send-btn:hover { transform: scale(1.05); filter: brightness(1.1); }
        .chat-send-btn:active { transform: scale(0.96); }
        .chat-icon-btn { transition: all 0.2s; cursor: pointer; background: transparent; border: none; outline: none; }
        .chat-icon-btn:hover { color: #00a8e8 !important; transform: translateY(-3px); }
        .chat-msg-bubble { animation: chatFadeUp 0.35s cubic-bezier(0.16,1,0.3,1); }
        @keyframes chatFadeUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
        @keyframes chatBlink { 0%,100%{opacity:1} 50%{opacity:0.2} }
        .chat-typing-dot { animation: chatBlink 1.2s ease-in-out infinite; }
        .chat-typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .chat-typing-dot:nth-child(3) { animation-delay: 0.4s; }
        .chat-sidebar-anim { animation: chatSlideIn 0.4s cubic-bezier(0.16,1,0.3,1); }
        @keyframes chatSlideIn { from{opacity:0;transform:translateX(-12px)} to{opacity:1;transform:translateX(0)} }
      `}</style>

      {/* ─── SIDEBAR ─── */}
      {sidebarOpen && (
        <div
          className="chat-sidebar-anim flex-shrink-0 flex flex-col"
          style={{
            width: "268px",
            background: "#fff",
            borderRight: "1.5px solid #e8edf5",
            boxShadow: "2px 0 16px rgba(0,0,0,0.04)",
          }}
        >
          <div style={{ padding: "20px 18px 14px", borderBottom: "1px solid #f1f3f8" }}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div
                  style={{
                    width: "28px",
                    height: "28px",
                    borderRadius: "8px",
                    background: "linear-gradient(135deg, #FA5C5C, #FD8A6B)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    boxShadow: "0 2px 8px rgba(250,92,92,0.3)",
                  }}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                      stroke="white"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                </div>
                <span style={{ fontSize: "13px", fontWeight: 800, color: "#0d1b2a", letterSpacing: "-0.3px" }}>
                  Chat History
                </span>
              </div>
              <button
                type="button"
                className="chat-icon-btn"
                onClick={() => setSidebarOpen(false)}
                style={{ color: "#9ca3af", padding: "4px" }}
                aria-label="Close sidebar"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                  <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </button>
            </div>
            <button
              type="button"
              onClick={handleNewChat}
              className="w-full flex items-center gap-2 py-2 px-3 rounded-lg border-2 border-dashed border-gray-200 text-gray-600 text-sm font-semibold hover:border-[#00a8e8] hover:text-[#00a8e8] hover:bg-[rgba(0,168,232,0.05)] transition-all"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
              </svg>
              New Chat
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-2">
            {(["Today", "Yesterday", "Earlier"] as const).map((group) => {
              const items = groupedHistory[group];
              if (!items.length) return null;
              return (
                <div key={group} className="mb-3">
                  <div
                    style={{
                      fontSize: "10px",
                      fontWeight: 700,
                      color: "#9ca3af",
                      letterSpacing: "0.8px",
                      textTransform: "uppercase",
                      padding: "0 8px 6px",
                    }}
                  >
                    {group}
                  </div>
                  {items.map((chat) => (
                    <div
                      key={chat.id}
                      className={`chat-hist-item ${activeChatId === chat.id ? "active" : ""}`}
                      role="button"
                      tabIndex={0}
                      onClick={() => setActiveChatId(chat.id)}
                      onKeyDown={(e) => e.key === "Enter" && setActiveChatId(chat.id)}
                      style={{
                        padding: "10px",
                        borderRadius: "10px",
                        marginBottom: "3px",
                        borderLeft: "3px solid transparent",
                        background: activeChatId === chat.id ? "rgba(0,168,232,0.1)" : "transparent",
                      }}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          style={{
                            fontSize: "9.5px",
                            fontWeight: 700,
                            padding: "2px 7px",
                            borderRadius: "20px",
                            flexShrink: 0,
                            background: `${SUBJECT_COLORS[chat.subject] || "#9ca3af"}18`,
                            color: SUBJECT_COLORS[chat.subject] || "#9ca3af",
                            border: `1px solid ${SUBJECT_COLORS[chat.subject] || "#9ca3af"}30`,
                          }}
                        >
                          {chat.subject}
                        </span>
                      </div>
                      <div
                        style={{
                          fontSize: "12px",
                          fontWeight: 700,
                          color: "#0d1b2a",
                          letterSpacing: "-0.2px",
                          marginBottom: "2px",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {chat.title}
                      </div>
                      <div
                        style={{
                          fontSize: "11px",
                          color: "#9ca3af",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {chat.preview}
                      </div>
                    </div>
                  ))}
                </div>
              );
            })}
            {historyItems.length === 0 && (
              <p style={{ fontSize: "12px", color: "#9ca3af", padding: "8px" }}>No recent chats</p>
            )}
          </div>

          <div style={{ padding: "12px 14px", borderTop: "1px solid #f1f3f8" }}>
            <div
              className="flex items-center gap-2 p-2 rounded-lg"
              style={{ background: "#f8f9fc" }}
            >
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "8px",
                  background: "linear-gradient(135deg, #00a8e8, #0077b6)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="white">
                  <path d="M13 10V3L4 14h7v7l9-11h-7z" fill="white" />
                </svg>
              </div>
              <div className="min-w-0 flex-1">
                <div style={{ fontSize: "11px", fontWeight: 700, color: "#0d1b2a" }}>
                  Llama 3.2 · RAG
                </div>
                <div style={{ fontSize: "10px", color: "#9ca3af" }}>
                  {isOnline ? "Online" : "Offline"} · Local
                </div>
              </div>
              <div
                style={{
                  width: "7px",
                  height: "7px",
                  borderRadius: "50%",
                  background: isOnline ? "#10b981" : "#9ca3af",
                  flexShrink: 0,
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* ─── MAIN AREA ─── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div
          className="flex items-center gap-3 px-6 flex-shrink-0"
          style={{
            background: "#fff",
            borderBottom: "1.5px solid #e8edf5",
            height: "68px",
            boxShadow: "0 2px 12px rgba(0,0,0,0.04)",
          }}
        >
          {!sidebarOpen && (
            <button
              type="button"
              className="chat-icon-btn"
              onClick={() => setSidebarOpen(true)}
              style={{ color: "#6b7280", padding: "6px", borderRadius: "8px" }}
              aria-label="Open sidebar"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M3 12h18M3 6h18M3 18h18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          )}
          <Link
            to="/dashboard"
            className="flex items-center gap-1 py-1.5 px-2.5 rounded-lg text-gray-600 text-sm font-medium hover:bg-[#f1f3f8] hover:text-[#0d1b2a] transition-colors"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
              <path d="M19 12H5M5 12l7-7M5 12l7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Dashboard
          </Link>
          <div style={{ width: "1px", height: "28px", background: "#e8edf5" }} />
          <div
            style={{
              width: "38px",
              height: "38px",
              borderRadius: "11px",
              background: "linear-gradient(135deg, #00a8e8, #0077b6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
              boxShadow: "0 3px 10px rgba(0,168,232,0.35)",
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path
                d="M9.663 17h4.673M12 3v1m0 16v1M4.22 4.22l.707.707m12.727 12.727.707.707M3 12h1m16 0h1"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <circle cx="12" cy="12" r="4" stroke="white" strokeWidth="2" />
            </svg>
          </div>
          <div>
            <div style={{ fontSize: "15px", fontWeight: 800, color: "#0d1b2a", letterSpacing: "-0.4px" }}>
              AI Tutor Chat
            </div>
            <div style={{ fontSize: "11px", color: "#9ca3af", fontWeight: 500 }}>
              Powered by Llama 3.2 · RAG-grounded
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <div
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5"
              style={{
                background: isOnline ? "rgba(16,185,129,0.08)" : "rgba(156,163,175,0.1)",
                border: `1px solid ${isOnline ? "rgba(16,185,129,0.2)" : "rgba(156,163,175,0.2)"}`,
              }}
            >
              <span
                style={{
                  width: "7px",
                  height: "7px",
                  borderRadius: "50%",
                  background: isOnline ? "#10b981" : "#9ca3af",
                  display: "inline-block",
                }}
              />
              <span style={{ fontSize: "12px", fontWeight: 600, color: isOnline ? "#10b981" : "#9ca3af" }}>
                {isOnline ? "Online" : "Offline"}
              </span>
            </div>
            <select
              value={level}
              onChange={(e) => handleLevelChange(e.target.value)}
              style={{
                appearance: "none",
                background: "#f8f9fc",
                border: "1.5px solid #e5e7eb",
                borderRadius: "9px",
                padding: "7px 32px 7px 12px",
                fontSize: "12.5px",
                fontWeight: 600,
                color: "#374151",
                fontFamily: "inherit",
              }}
              aria-label="Difficulty level"
            >
              {LEVELS.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={handleClear}
              className="px-3 py-1.5 rounded-lg border-2 border-gray-200 text-gray-600 text-sm font-semibold hover:border-[#FA5C5C] hover:text-[#FA5C5C] hover:bg-[#fff5f5] transition-all"
            >
              Clear
            </button>
          </div>
        </div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto p-7">
          {displayMessages.length === 1 && displayMessages[0].role === "assistant" && !loading && (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <div>
                <svg width="52" height="52" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M12 2l2 4.5 5 .5-3.5 3.5.8 5L12 13l-4.3 2.5.8-5L5 7l5-.5L12 2z"
                    fill="url(#chatGrad)"
                  />
                  <path d="M19 5l1 2.2 2.2 1-2.2 1L19 11.2l-1-2.2-2.2-1 2.2-1L19 5z" fill="#FEC288" />
                  <path d="M5 15l.7 1.5 1.5.7-1.5.7-.7 1.5-.7-1.5-1.5-.7 1.5-.7L5 15z" fill="#FA5C5C" />
                  <defs>
                    <linearGradient id="chatGrad" x1="5" y1="2" x2="19" y2="16">
                      <stop stopColor="#FA5C5C" />
                      <stop offset="0.5" stopColor="#FD8A6B" />
                      <stop offset="1" stopColor="#FEC288" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>
              <div className="text-center">
                <div
                  style={{
                    fontSize: "17px",
                    fontWeight: 800,
                    color: "#0d1b2a",
                    marginBottom: "6px",
                    letterSpacing: "-0.4px",
                  }}
                >
                  Ask me anything from your textbooks.
                </div>
                <div style={{ fontSize: "13.5px", color: "#9ca3af", fontWeight: 400 }}>
                  I&apos;m fully offline — no internet needed.
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2.5 mt-2 w-full max-w-[420px]">
                {QUICK_ACTIONS.map((a, i) => (
                  <button
                    key={i}
                    type="button"
                    className="chat-action-btn flex items-center gap-2 py-3 px-4 rounded-xl bg-white border-2 border-[#e8edf5] text-[#374151] text-sm font-bold text-left hover:border-[#00a8e8] hover:text-[#00a8e8] hover:bg-[rgba(0,168,232,0.04)]"
                    onClick={() => {
                      setInput(a.prompt);
                      textareaRef.current?.focus();
                    }}
                  >
                    <span style={{ color: "#00a8e8", flexShrink: 0 }}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                        <path
                          d="M12 3v1m0 16v1M4.22 4.22l.707.707m12.727 12.727.707.707M3 12h1m16 0h1M4.927 19.073l.707-.707M18.364 5.636l.707-.707"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                        />
                        <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="2" />
                      </svg>
                    </span>
                    {a.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {displayMessages.map((msg, idx) => (
            <ChatBubble
              key={idx}
              message={msg}
              clarifyValue={clarifyInputs[idx] ?? ""}
              clarifyExpanded={clarifyExpanded[idx] ?? false}
              onClarifyChange={(v) => setClarifyInputs((p) => ({ ...p, [idx]: v }))}
              onClarifyToggle={() => setClarifyExpanded((p) => ({ ...p, [idx]: !p[idx] }))}
              onClarifySubmit={() => handleClarify(idx)}
              loading={loading}
            />
          ))}

          {loading && (
            <div className="chat-msg-bubble flex mb-4">
              <div
                style={{
                  width: "30px",
                  height: "30px",
                  borderRadius: "9px",
                  flexShrink: 0,
                  marginRight: "10px",
                  background: "linear-gradient(135deg, #00a8e8, #0077b6)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="3" stroke="white" strokeWidth="1.5" />
                </svg>
              </div>
              <div
                style={{
                  padding: "13px 18px",
                  borderRadius: "4px 16px 16px 16px",
                  background: "#fff",
                  border: "1.5px solid #e8edf5",
                  display: "flex",
                  gap: "5px",
                  alignItems: "center",
                  boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
                }}
              >
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="chat-typing-dot"
                    style={{
                      width: "7px",
                      height: "7px",
                      borderRadius: "50%",
                      background: "linear-gradient(135deg, #FA5C5C, #FD8A6B)",
                      display: "inline-block",
                    }}
                  />
                ))}
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {error && (
          <p className="px-6 py-2 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}

        {/* ─── INPUT BOX ─── */}
        <div className="flex-shrink-0 px-6 pb-5 pt-4">
          <div
            style={{
              position: "relative",
              background: "linear-gradient(to bottom right, #6b6b6b, #2c2c2c, #232323)",
              borderRadius: "18px",
              padding: "1.5px",
              boxShadow: "0 8px 32px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.1)",
            }}
          >
            <div
              style={{
                background: "rgba(10,12,18,0.92)",
                borderRadius: "17px",
                overflow: "visible",
              }}
            >
              <div className="pt-3.5 px-4">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={`Ask a question... (${level})`}
                  rows={2}
                  disabled={loading}
                  className="w-full bg-transparent text-[#f0f1f5] text-[13.5px] font-normal leading-relaxed resize-none outline-none border-none placeholder:text-white/35"
                />
              </div>
              <div className="flex items-center justify-between py-2.5 px-3.5 pb-3">
                <div className="flex gap-1.5 items-center">
                  {/* Attach: textbooks + upload */}
                  <div ref={attachRef} className="relative">
                    <button
                      type="button"
                      className={`chat-icon-btn p-1.5 rounded-md ${attachOpen ? "text-[#00a8e8]" : "text-white/25"}`}
                      title="Attach Textbook/PDF"
                      onClick={() => { setAttachOpen(!attachOpen); setSearchOpen(false); setSubjectOpen(false); }}
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                        <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  </div>
                  {/* Search: RAG / knowledge base */}
                  <div ref={searchRef} className="relative">
                    <button
                      type="button"
                      className={`chat-icon-btn p-1.5 rounded-md ${searchOpen ? "text-[#00a8e8]" : "text-white/25"}`}
                      title="Search Knowledge Base"
                      onClick={() => { setSearchOpen(!searchOpen); setAttachOpen(false); setSubjectOpen(false); }}
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                        <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2" />
                        <path d="m21 21-4.35-4.35" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                      </svg>
                    </button>
                  </div>
                  {/* Subject selector */}
                  <div ref={subjectRef} className="relative">
                    <button
                      type="button"
                      className={`chat-icon-btn p-1.5 rounded-md ${subjectOpen ? "text-[#00a8e8]" : "text-white/25"}`}
                      title="Select Subject"
                      onClick={() => { setSubjectOpen(!subjectOpen); setAttachOpen(false); setSearchOpen(false); }}
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                        <path d="M4 19.5A2.5 2.5 0 016.5 17H20M4 19.5A2.5 2.5 0 014 17V5a2 2 0 012-2h10a2 2 0 012 2v5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                        <path d="M14 13l2 2 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  </div>
                </div>
                {attachOpen &&
                  attachPos &&
                  createPortal(
                    <div
                      ref={attachDropdownRef}
                      className="min-w-[320px] max-w-[min(480px,95vw)] rounded-xl bg-[#1a1d24] border border-white/10 shadow-xl p-3 z-[9999] overflow-y-auto"
                      style={{
                        position: "fixed",
                        left: attachPos.left,
                        ...getDropdownPlacement(attachPos),
                      }}
                    >
                      <div className="text-xs font-semibold text-white/80 mb-2">Textbooks & notes</div>
                      <label className="block mb-2">
                        <span className="text-xs text-white/60">Upload PDF</span>
                        <input
                          type="file"
                          accept=".pdf"
                          onChange={handleTextbookUpload}
                          disabled={uploading}
                          className="block w-full mt-1 text-xs text-white/80 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:bg-[#00a8e8] file:text-white"
                        />
                      </label>
                      {textbooks.length > 0 && (
                        <>
                          <div className="text-xs text-white/60 mb-1">Existing</div>
                          <div className="max-h-40 overflow-y-auto space-y-1">
                            {textbooks.map((t) => (
                              <button
                                key={t.id}
                                type="button"
                                onClick={() => {
                                  setActiveTextbook(t.id);
                                  setAttachOpen(false);
                                }}
                                className={`block w-full text-left px-2 py-1.5 rounded text-xs break-words whitespace-normal ${activeTextbook === t.id ? "bg-[#00a8e8]/30 text-white" : "text-white/80 hover:bg-white/10"}`}
                              >
                                {t.name}
                              </button>
                            ))}
                          </div>
                        </>
                      )}
                      {activeTextbook && (
                        <button
                          type="button"
                          onClick={() => setActiveTextbook(null)}
                          className="mt-2 text-xs text-white/50 hover:text-white/80"
                        >
                          Clear selection
                        </button>
                      )}
                    </div>,
                    document.body,
                    "attach-dropdown"
                  )}
                {searchOpen &&
                  searchPos &&
                  createPortal(
                    <div
                      ref={searchDropdownRef}
                      className="min-w-[300px] max-w-[min(420px,90vw)] rounded-xl bg-[#1a1d24] border border-white/10 shadow-xl p-3 z-[9999] overflow-y-auto"
                      style={{
                        position: "fixed",
                        left: searchPos.left,
                        ...getDropdownPlacement(searchPos),
                      }}
                    >
                      <div className="text-xs font-semibold text-white/80 mb-2">Search textbooks</div>
                      <div className="flex gap-1 mb-2">
                        <input
                          type="text"
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && handleRagSearch()}
                          placeholder="Query..."
                          className="flex-1 px-2 py-1.5 rounded bg-white/10 text-white text-xs placeholder:text-white/40 border border-white/10"
                        />
                        <button
                          type="button"
                          onClick={handleRagSearch}
                          disabled={searching || !searchQuery.trim()}
                          className="px-2 py-1.5 rounded bg-[#00a8e8] text-white text-xs font-medium disabled:opacity-50"
                        >
                          Search
                        </button>
                      </div>
                      {searchResults.length > 0 && (
                        <div className="max-h-36 overflow-y-auto space-y-1 text-xs text-white/70">
                          {searchResults.map((r, i) => (
                            <div
                              key={i}
                              className="p-2 rounded bg-white/5 border border-white/5 break-words whitespace-normal text-xs"
                            >
                              {r.content?.slice(0, 200)}
                              {(r.content?.length ?? 0) > 200 ? "…" : ""}
                            </div>
                          ))}
                        </div>
                      )}
                      {searchResults.length === 0 && searchQuery && !searching && (
                        <p className="text-xs text-white/50">No matches. Try different keywords.</p>
                      )}
                    </div>,
                    document.body,
                    "search-dropdown"
                  )}
                {subjectOpen &&
                  subjectPos &&
                  createPortal(
                    <div
                      ref={subjectDropdownRef}
                      className="min-w-[200px] max-w-[min(280px,95vw)] rounded-xl bg-[#1a1d24] border border-white/10 shadow-xl p-2 z-[9999] overflow-y-auto"
                      style={{
                        position: "fixed",
                        left: subjectPos.left,
                        ...getDropdownPlacement(subjectPos),
                      }}
                    >
                      <div className="text-xs font-semibold text-white/80 mb-2">Subject</div>
                      <div className="space-y-0.5">
                        {SUBJECTS.map((s) => (
                          <button
                            key={s}
                            type="button"
                            onClick={() => {
                              setSubject(s);
                              setSubjectOpen(false);
                            }}
                            className={`block w-full text-left px-2 py-1.5 rounded text-xs ${subject === s ? "bg-[#00a8e8]/30 text-white" : "text-white/80 hover:bg-white/10"}`}
                          >
                            {s}
                          </button>
                        ))}
                      </div>
                    </div>,
                    document.body,
                    "subject-dropdown"
                  )}
                <button
                  type="button"
                  className="chat-send-btn flex items-center gap-2 pl-3 pr-1 py-0.5 rounded-xl border-none text-sm font-bold disabled:opacity-60 disabled:cursor-not-allowed"
                  style={{
                    background: input.trim()
                      ? "linear-gradient(135deg, #059669, #10b981)"
                      : "linear-gradient(to top, #292929, #555, #292929)",
                    color: input.trim() ? "#fff" : "#6b6b6b",
                    boxShadow: input.trim()
                      ? "0 3px 12px rgba(16,185,129,0.4), inset 0 1px 0 rgba(255,255,255,0.2)"
                      : "inset 0 4px 2px -3px rgba(255,255,255,0.3)",
                  }}
                  onClick={handleSend}
                  disabled={loading || !input.trim()}
                >
                  Send
                  <span
                    style={{
                      width: "30px",
                      height: "30px",
                      borderRadius: "10px",
                      background: input.trim() ? "rgba(255,255,255,0.2)" : "rgba(0,0,0,0.15)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 512 512" fill="currentColor">
                      <path d="M473 39.05a24 24 0 0 0-25.5-5.46L47.47 185h-.08a24 24 0 0 0 1 45.16l.41.13 137.3 58.63a16 16 0 0 0 15.54-3.59L422 80a7.07 7.07 0 0 1 10 10L226.66 310.26a16 16 0 0 0-3.59 15.54l58.65 137.38c.06.2.12.38.19.57c3.2 9.27 11.3 15.81 21.09 16.25h1a24.63 24.63 0 0 0 23-15.46L478.39 64.62A24 24 0 0 0 473 39.05" />
                    </svg>
                  </span>
                </button>
              </div>
            </div>
          </div>
          <div className="flex gap-2 mt-2.5 flex-wrap">
            {QUICK_CHIPS.map((chip, i) => (
              <button
                key={i}
                type="button"
                className="py-1.5 px-3 rounded-full text-xs font-semibold text-gray-600 bg-white/70 border border-white/90 hover:border-[#FD8A6B] hover:text-[#FD8A6B] hover:bg-[rgba(253,138,107,0.08)] transition-all"
                onClick={() => {
                  setInput(chip);
                  textareaRef.current?.focus();
                }}
              >
                {chip}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatBubble({
  message,
  clarifyValue,
  clarifyExpanded,
  onClarifyChange,
  onClarifyToggle,
  onClarifySubmit,
  loading,
}: {
  message: ChatMessage;
  clarifyValue: string;
  clarifyExpanded: boolean;
  onClarifyChange: (v: string) => void;
  onClarifyToggle: () => void;
  onClarifySubmit: () => void;
  loading: boolean;
}) {
  const isUser = message.role === "user";
  const isClarify = message.is_clarification === true;

  if (isUser) {
    return (
      <div className="chat-msg-bubble flex justify-end mb-4">
        <div
          style={{
            maxWidth: "68%",
            padding: "12px 16px",
            borderRadius: "16px 4px 16px 16px",
            background: "linear-gradient(135deg, #FA5C5C, #FD8A6B)",
            color: "#fff",
            fontSize: "13.5px",
            fontWeight: 400,
            lineHeight: 1.6,
            boxShadow: "0 4px 14px rgba(250,92,92,0.3)",
          }}
        >
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`chat-msg-bubble flex mb-4 ${isClarify ? "ml-5" : ""}`}>
      <div
        style={{
          width: "30px",
          height: "30px",
          borderRadius: "9px",
          flexShrink: 0,
          marginRight: "10px",
          marginTop: "2px",
          background: "linear-gradient(135deg, #00a8e8, #0077b6)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 2px 8px rgba(0,168,232,0.3)",
        }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path
            d="M9.663 17h4.673M12 3v1m0 16v1M4.22 4.22l.707.707m12.727 12.727.707.707M3 12h1m16 0h1"
            stroke="white"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <circle cx="12" cy="12" r="3" stroke="white" strokeWidth="1.5" />
        </svg>
      </div>
      <div className="min-w-0 flex-1">
        <div
          style={{
            maxWidth: "68%",
            padding: "12px 16px",
            borderRadius: "4px 16px 16px 16px",
            background: "#fff",
            color: "#1a2035",
            fontSize: "13.5px",
            fontWeight: 400,
            lineHeight: 1.6,
            boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
            border: "1.5px solid #e8edf5",
          }}
        >
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
        <div className="mt-2">
          <button
            type="button"
            onClick={onClarifyToggle}
            className="text-xs font-medium text-[#00a8e8] hover:underline"
          >
            {clarifyExpanded ? "Hide" : "Clarify this"}
          </button>
          {clarifyExpanded && (
            <div className="mt-2 flex flex-col gap-2">
              <input
                type="text"
                value={clarifyValue}
                onChange={(e) => onClarifyChange(e.target.value)}
                placeholder="What part needs more explanation?"
                className="w-full px-3 py-2 rounded-lg bg-white border border-gray-200 text-gray-900 text-sm"
                aria-label="Clarification question"
              />
              <button
                type="button"
                onClick={onClarifySubmit}
                disabled={loading || !clarifyValue.trim()}
                className="self-start px-3 py-1.5 rounded-lg bg-[#00a8e8] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50"
              >
                Get Clarification
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
