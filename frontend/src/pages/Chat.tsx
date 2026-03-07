/**
 * Chat page — AI Tutor Chat with message bubbles, difficulty, clear, clarify.
 * Persists chat_history via GET/PUT /api/user/stats.
 */

import { useCallback, useEffect, useState } from "react";
import { PageChrome } from "../components/PageChrome";
import { StatusIndicator } from "../components/StatusIndicator";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { useAuth } from "../contexts/AuthContext";
import {
  getUserStats,
  updateUserStats,
  postChat,
  type ChatMessage,
} from "../services/api";

const MAX_HISTORY = 50;
const DIFFICULTY_OPTIONS = ["Beginner", "Intermediate", "Expert"] as const;

function formatTime(iso: string): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

export function ChatPage() {
  const { profile, connectivityStatus } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [difficulty, setDifficulty] = useState<string>("Beginner");
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState("");
  const [clarifyInputs, setClarifyInputs] = useState<Record<number, string>>({});
  const [clarifyExpanded, setClarifyExpanded] = useState<Record<number, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  const loadInitial = useCallback(async () => {
    try {
      const stats = await getUserStats();
      const hist = stats.chat_history;
      if (Array.isArray(hist)) {
        setMessages(hist.slice(-MAX_HISTORY));
      }
      const diff = stats.preferences?.difficulty_level;
      if (diff && DIFFICULTY_OPTIONS.includes(diff as (typeof DIFFICULTY_OPTIONS)[number])) {
        setDifficulty(diff);
      }
    } catch {
      setMessages([]);
    }
  }, []);

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  const saveHistory = useCallback(async (next: ChatMessage[]) => {
    setMessages(next);
    try {
      await updateUserStats({ chat_history: next.slice(-MAX_HISTORY) });
    } catch {
      // ignore
    }
  }, []);

  const sendMessage = useCallback(
    async (text: string, isClarification: boolean = false) => {
      if (!text.trim()) return;
      setError(null);
      const userMsg: ChatMessage = {
        role: "user",
        content: text.trim(),
        timestamp: new Date().toISOString(),
        is_clarification: isClarification,
      };
      const next = [...messages, userMsg];
      await saveHistory(next);
      setLoading(true);
      try {
        const res = await postChat({
          message: text.trim(),
          is_clarification: isClarification,
          context: {
            difficulty,
            chat_history: next.slice(-20).map((m) => ({ role: m.role, content: m.content })),
            subject: "[ACTIVE_SUBJECT]",
            active_textbook: "[ACTIVE_TEXTBOOK]",
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
          content: "I couldn't complete that request. Please check that Ollama is running and try again.",
          timestamp: new Date().toISOString(),
          is_clarification: isClarification,
        };
        await saveHistory([...next, fallback]);
      } finally {
        setLoading(false);
      }
    },
    [messages, difficulty, profile.profile_name, saveHistory]
  );

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (loading || !input.trim()) return;
      const text = input;
      setInput("");
      sendMessage(text, false);
    },
    [input, loading, sendMessage]
  );

  const handleClear = useCallback(async () => {
    setMessages([]);
    setClarifyInputs({});
    setClarifyExpanded({});
    setError(null);
    try {
      await updateUserStats({ chat_history: [] });
    } catch {
      // ignore
    }
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

  const handleDifficultyChange = useCallback(
    (newDiff: string) => {
      setDifficulty(newDiff);
      updateUserStats({ preferences: { difficulty_level: newDiff } }).catch(() => {});
    },
    []
  );

  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <div className="flex flex-col h-[calc(100vh-8rem)] max-h-[700px]">
        {/* Header */}
        <div className="glass-panel rounded-xl border border-glass-border p-4 flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl bg-accent-blue/20 border border-accent-blue/40 flex items-center justify-center text-lg"
              aria-hidden
            >
              🤖
            </div>
            <div>
              <h2 className="text-lg font-semibold text-primary">AI Tutor Chat</h2>
              <p className="text-xs text-primary/60">Powered by Llama 3.2 - RAG-grounded</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <StatusIndicator
              status={connectivityStatus}
              label={connectivityStatus === "online" ? "● Online" : "○ Offline - AI works fully offline"}
            />
            <select
              value={difficulty}
              onChange={(e) => handleDifficultyChange(e.target.value)}
              className="px-3 py-2 rounded-lg bg-surface-light border border-glass-border text-primary text-sm font-medium"
              aria-label="Difficulty level"
            >
              {DIFFICULTY_OPTIONS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={handleClear}
              className="px-3 py-2 rounded-lg border border-glass-border text-primary/80 text-sm font-medium hover:bg-surface-light"
            >
              Clear
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-2">
          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="text-4xl mb-3 opacity-80">🤖</div>
              <p className="text-primary/80">
                Ask me anything from your textbooks.
                <br />
                I&apos;m fully offline — no internet needed.
              </p>
            </div>
          )}
          {messages.map((msg, idx) => (
            <ChatBubble
              key={idx}
              message={msg}
              index={idx}
              clarifyValue={clarifyInputs[idx] ?? ""}
              clarifyExpanded={clarifyExpanded[idx] ?? false}
              onClarifyChange={(v) => setClarifyInputs((p) => ({ ...p, [idx]: v }))}
              onClarifyToggle={() =>
                setClarifyExpanded((p) => ({ ...p, [idx]: !p[idx] }))
              }
              onClarifySubmit={() => handleClarify(idx)}
              loading={loading}
            />
          ))}
          {loading && (
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-surface-light border border-glass-border flex items-center justify-center flex-shrink-0">
                🤖
              </div>
              <div className="flex-1 min-w-0">
                <LoadingSpinner message="AI Tutor is preparing a response..." />
              </div>
            </div>
          )}
        </div>

        {error && (
          <p className="text-sm text-error mt-2" role="alert">
            {error}
          </p>
        )}

        {/* Input */}
        <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={`Ask a question… (${difficulty})`}
            className="flex-1 px-4 py-3 rounded-xl bg-surface-light border border-glass-border text-primary placeholder:text-primary/50 focus:outline-none focus:ring-2 focus:ring-accent-blue"
            disabled={loading}
            aria-label="Chat message"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-5 py-3 rounded-xl bg-accent-blue text-deep font-semibold hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </form>
      </div>
    </PageChrome>
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
  index: number;
  clarifyValue: string;
  clarifyExpanded: boolean;
  onClarifyChange: (v: string) => void;
  onClarifyToggle: () => void;
  onClarifySubmit: () => void;
  loading: boolean;
}) {
  const isUser = message.role === "user";
  const isClarify = message.is_clarification === true;
  const ts = formatTime(message.timestamp);

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%]">
          <div className="rounded-2xl rounded-tr-md px-4 py-3 bg-accent-blue/20 border border-accent-blue/40 text-primary">
            <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
          </div>
          <p className="text-xs text-primary/50 mt-1 text-right">You · {ts}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex justify-start ${isClarify ? "ml-5" : ""}`}>
      <div className="max-w-[85%] flex gap-2">
        <div
          className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm flex-shrink-0 ${
            isClarify ? "bg-primary/10" : "bg-accent-blue/20 border border-accent-blue/40"
          }`}
          aria-hidden
        >
          🤖
        </div>
        <div className="min-w-0 flex-1">
          <div
            className={`rounded-2xl rounded-tl-md px-4 py-3 border text-primary ${
              isClarify
                ? "bg-surface-light border-glass-border"
                : "bg-surface-light border-glass-border"
            }`}
          >
            <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
          </div>
          <p className="text-xs text-primary/50 mt-1">
            {isClarify ? "Clarification" : "AI Tutor"} · {ts}
          </p>
          {!isClarify && (
            <div className="mt-2">
              <button
                type="button"
                onClick={onClarifyToggle}
                className="text-xs font-medium text-accent-blue hover:underline"
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
                    className="w-full px-3 py-2 rounded-lg bg-surface-light border border-glass-border text-primary text-sm placeholder:text-primary/50"
                    aria-label="Clarification question"
                  />
                  <button
                    type="button"
                    onClick={onClarifySubmit}
                    disabled={loading || !clarifyValue.trim()}
                    className="self-start px-3 py-1.5 rounded-lg bg-accent-blue text-deep text-sm font-medium hover:opacity-90 disabled:opacity-50"
                  >
                    Get Clarification
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
