/**
 * Textbook Archive page — dark-themed drag-and-drop upload for PDF/PPTX.
 * Uses same backend storage as Flashcards and AI Chat. Scoped CSS to avoid theme bleed.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { PageChrome } from "../components/PageChrome";
import {
  getTextbooks,
  uploadTextbookWithProgress,
  type TextbooksResponse,
} from "../services/api";
import "./Textbooks.css";

type QueueItem = {
  id: string;
  file: File;
  name: string;
  size: number;
  status: "pending" | "uploading" | "complete" | "error";
  progress: number;
  error?: string;
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function TextbooksPage() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [existingTextbooks, setExistingTextbooks] = useState<
    TextbooksResponse["textbooks"]
  >([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refreshTextbooks = useCallback(() => {
    getTextbooks()
      .then((r) => setExistingTextbooks(r.textbooks))
      .catch(() => setExistingTextbooks([]));
  }, []);

  useEffect(() => {
    refreshTextbooks();
  }, [refreshTextbooks]);

  const addFiles = useCallback((files: FileList | File[]) => {
    const allowed = [".pdf", ".pptx"];
    const toAdd: QueueItem[] = [];
    for (const f of Array.from(files)) {
      const ext = "." + (f.name.split(".").pop() || "").toLowerCase();
      if (!allowed.includes(ext)) continue;
      toAdd.push({
        id: `${f.name}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        file: f,
        name: f.name,
        size: f.size,
        status: "pending",
        progress: 0,
      });
    }
    setQueue((prev) => [...prev, ...toAdd]);
  }, []);

  const uploadOne = useCallback(
    async (item: QueueItem) => {
      setQueue((prev) =>
        prev.map((q) =>
          q.id === item.id
            ? { ...q, status: "uploading" as const, progress: 0 }
            : q
        )
      );

      const onProgress = (loaded: number, total: number) => {
        const pct = total > 0 ? Math.round((loaded / total) * 100) : 0;
        setQueue((prev) =>
          prev.map((q) =>
            q.id === item.id ? { ...q, progress: pct } : q
          )
        );
      };

      try {
        await uploadTextbookWithProgress(item.file, onProgress);
        setQueue((prev) =>
          prev.map((q) =>
            q.id === item.id
              ? { ...q, status: "complete" as const, progress: 100 }
              : q
          )
        );
        refreshTextbooks();
      } catch (err) {
        setQueue((prev) =>
          prev.map((q) =>
            q.id === item.id
              ? {
                  ...q,
                  status: "error" as const,
                  error: err instanceof Error ? err.message : "Upload failed",
                }
              : q
          )
        );
      }
    },
    [refreshTextbooks]
  );

  const handleSync = useCallback(async () => {
    const pending = queue.filter((q) => q.status === "pending");
    if (pending.length === 0) return;
    setSyncing(true);
    for (const item of pending) {
      await uploadOne(item);
    }
    setSyncing(false);
  }, [queue, uploadOne]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (e.dataTransfer?.files?.length) addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files?.length) addFiles(files);
      e.target.value = "";
    },
    [addFiles]
  );

  const pendingCount = queue.filter((q) => q.status === "pending").length;

  return (
    <PageChrome backTo="/dashboard" backLabel="← Back to Dashboard">
      <div className="textbooks-archive">
        <div className="tb-prism-canvas">
          <div className="tb-light-leak tb-leak-1" />
          <div className="tb-light-leak tb-leak-2" />
          <div className="tb-light-leak tb-leak-3" />
        </div>

        <main className="tb-app-container">
          <div className="tb-intersection-node" aria-hidden />
          <div className="tb-glass-refraction" aria-hidden />

          <label
            className="tb-drop-zone"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={handleClick}
            onMouseMove={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const x = ((e.clientX - rect.left) / rect.width) * 100;
              const y = ((e.clientY - rect.top) / rect.height) * 100;
              const overlay = e.currentTarget.querySelector(
                ".tb-dichroic-overlay"
              ) as HTMLElement;
              if (overlay) {
                overlay.style.background = `
                  radial-gradient(circle at ${x}% ${y}%,
                    rgba(0, 168, 232, 0.12) 0%,
                    rgba(253, 138, 107, 0.08) 30%,
                    transparent 70%)
                `;
              }
            }}
            onMouseLeave={(e) => {
              const overlay = e.currentTarget.querySelector(
                ".tb-dichroic-overlay"
              ) as HTMLElement;
              if (overlay) overlay.style.background = "";
            }}
          >
            <div className="tb-dichroic-overlay" aria-hidden />
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.pptx"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />
            <header>
              <div className="tb-header-meta">Textbooks — Studaxis</div>
              <h1 className="tb-h1">
                Import
                <br />
                Curriculum
                <br />
                Assets
              </h1>
            </header>
            <div className="tb-prism-intersection" aria-hidden />
            <div className="tb-upload-prompt">
              <p>
              Simply drop your textbooks or slides here to start learning instantly.
              </p>
              <div className="tb-file-types">
                <span className="tb-type-tag">PDF</span>
                <span className="tb-type-tag">PPTX</span>
              </div>
            </div>
          </label>

          <section className="tb-queue-panel">
            <div className="tb-queue-header">
              <span>QUEUE</span>
              <span>{queue.length} ITEMS</span>
            </div>
            {existingTextbooks.length > 0 && (
              <div className="tb-file-list" style={{ borderBottom: "1px solid var(--tb-border)", paddingBottom: 16, marginBottom: 8 }}>
                <div style={{ fontSize: 10, color: "var(--tb-subtle)", textTransform: "uppercase", marginBottom: 12 }}>
                  Library ({existingTextbooks.length})
                </div>
                {existingTextbooks.slice(0, 5).map((t) => (
                  <div key={t.id} className="tb-file-name" style={{ padding: "4px 0", opacity: 0.9 }}>
                    {t.name}
                  </div>
                ))}
                {existingTextbooks.length > 5 && (
                  <div style={{ fontSize: 11, color: "var(--tb-subtle)" }}>
                    +{existingTextbooks.length - 5} more
                  </div>
                )}
              </div>
            )}
            <div className="tb-file-list">
              {queue.length === 0 ? (
                <p style={{ color: "var(--tb-subtle)", fontSize: 13 }}>
                  {existingTextbooks.length === 0
                    ? "Drop files or click to add."
                    : "Happy Learning!"}
                </p>
              ) : (
                queue.map((item) => (
                  <div
                    key={item.id}
                    className="tb-file-item"
                    style={{
                      opacity: item.status === "error" ? 0.6 : 1,
                    }}
                  >
                    <div className="tb-file-name">{item.name}</div>
                    <div className="tb-file-meta">
                      <span>{formatSize(item.size)}</span>
                      <span>
                        {item.status === "pending"
                          ? "PENDING"
                          : item.status === "uploading"
                            ? `${item.progress}%`
                            : item.status === "complete"
                              ? "COMPLETE"
                              : "ERROR"}
                      </span>
                    </div>
                    <div className="tb-progress-bar">
                      <div
                        className={`tb-progress-fill ${item.status === "complete" ? "tb-complete" : ""}`}
                        style={{ width: `${item.progress}%` }}
                      />
                    </div>
                    {item.error && (
                      <span
                        style={{
                          fontSize: 10,
                          color: "var(--tb-accent-warm)",
                        }}
                      >
                        {item.error}
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>
            <button
              type="button"
              className="tb-submit-btn"
              onClick={handleSync}
              disabled={pendingCount === 0 || syncing}
            >
              {syncing ? "Uploading…" : "Synchronize Library"}
            </button>
          </section>
        </main>
      </div>
    </PageChrome>
  );
}
