/**
 * FlashcardSourceSelector — Textbook (TX), Web link (WI), Files (FL) generation sources.
 * Textbook: existing textbooks or upload new PDF. Web link: site URLs. Files: txt, pdf, ppt.
 */

import { useState, useEffect, useRef } from "react";
import {
  getTextbooks,
  uploadTextbook,
  generateFlashcardsFromTextbook,
  generateFlashcardsFromWeblink,
  generateFlashcardsFromFiles,
} from "../services/api";
import type { FlashcardItem } from "../services/api";
import { LoadingSpinner } from "./LoadingSpinner";

export type SourceTab = "textbook" | "weblink" | "files";

export interface FlashcardSourceSelectorProps {
  count: number;
  onCountChange: (n: number) => void;
  onGenerate: (cards: FlashcardItem[], sourceType: string[]) => void;
  /** Optional: parent-controlled loading (e.g. when saving). Uses internal loading for API calls if not provided. */
  loading?: boolean;
  error: string | null;
  onError: (msg: string | null) => void;
}

export function FlashcardSourceSelector({
  count,
  onCountChange,
  onGenerate,
  loading: loadingProp,
  error,
  onError,
}: FlashcardSourceSelectorProps) {
  const [tab, setTab] = useState<SourceTab>("textbook");
  const [internalLoading, setInternalLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const loading = loadingProp ?? internalLoading;
  const [textbooks, setTextbooks] = useState<{ id: string; name: string }[]>([]);
  const [textbookMode, setTextbookMode] = useState<"existing" | "upload">("existing");
  const [selectedTextbook, setSelectedTextbook] = useState("");
  const [chapterInput, setChapterInput] = useState("");
  const [weblinkUrl, setWeblinkUrl] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getTextbooks()
      .then((r) => setTextbooks(r.textbooks))
      .catch(() => setTextbooks([]));
  }, []);

  const handleTextbookUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      onError("Please select a PDF file.");
      return;
    }
    onError(null);
    setUploading(true);
    try {
      const res = await uploadTextbook(file);
      setTextbooks((prev) => [...prev, { id: res.id, name: res.name }]);
      setSelectedTextbook(res.id);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
    e.target.value = "";
  };

  const handleGenerateTextbook = async () => {
    if (!selectedTextbook) {
      onError("Select or upload a textbook first.");
      return;
    }
    onError(null);
    setInternalLoading(true);
    try {
      const res = await generateFlashcardsFromTextbook({
        textbook_id: selectedTextbook,
        chapter: chapterInput.trim() || undefined,
        count,
      });
      const withSource = res.cards.map((c) => ({ ...c, sourceType: ["textbook"] }));
      onGenerate(withSource, ["textbook"]);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setInternalLoading(false);
    }
  };

  const handleGenerateWeblink = async () => {
    const url = weblinkUrl.trim();
    if (!url) {
      onError("Enter a valid URL.");
      return;
    }
    onError(null);
    setInternalLoading(true);
    try {
      const res = await generateFlashcardsFromWeblink({ url, count });
      const withSource = res.cards.map((c) => ({ ...c, sourceType: ["weblink"] }));
      onGenerate(withSource, ["weblink"]);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setInternalLoading(false);
    }
  };

  const handleGenerateFiles = async () => {
    if (files.length === 0) {
      onError("Select one or more files (txt, pdf, ppt).");
      return;
    }
    onError(null);
    setInternalLoading(true);
    try {
      const res = await generateFlashcardsFromFiles({ files, count });
      const withSource = res.cards.map((c) => ({ ...c, sourceType: ["file"] }));
      onGenerate(withSource, ["file"]);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setInternalLoading(false);
    }
  };

  const handleGenerate = () => {
    if (tab === "textbook") handleGenerateTextbook();
    else if (tab === "weblink") handleGenerateWeblink();
    else handleGenerateFiles();
  };

  const addFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const chosen = Array.from(e.target.files ?? []);
    const allowed = chosen.filter((f) => {
      const n = f.name.toLowerCase();
      return n.endsWith(".txt") || n.endsWith(".pdf") || n.endsWith(".ppt") || n.endsWith(".pptx");
    });
    setFiles((prev) => [...prev, ...allowed]);
    e.target.value = "";
  };

  const removeFile = (i: number) => setFiles((prev) => prev.filter((_, idx) => idx !== i));

  const tabs: { key: SourceTab; label: string; title: string }[] = [
    { key: "textbook", label: "TX", title: "Textbook" },
    { key: "weblink", label: "WI", title: "Web link" },
    { key: "files", label: "FL", title: "Files" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {tabs.map(({ key, label, title }) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              tab === key
                ? "bg-accent-blue text-white"
                : "border border-glass-border bg-surface-light text-primary hover:bg-surface-light/80"
            }`}
            title={title}
          >
            {label} — {title}
          </button>
        ))}
      </div>

      {tab === "textbook" && (
        <div className="space-y-4">
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="textbookMode"
                checked={textbookMode === "existing"}
                onChange={() => setTextbookMode("existing")}
                className="rounded border-glass-border accent-accent-blue"
              />
              <span className="text-sm text-primary">Existing textbooks</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="textbookMode"
                checked={textbookMode === "upload"}
                onChange={() => setTextbookMode("upload")}
                className="rounded border-glass-border accent-accent-blue"
              />
              <span className="text-sm text-primary">Upload new PDF</span>
            </label>
          </div>
          {textbookMode === "upload" && (
            <div>
              <input
                type="file"
                accept=".pdf"
                onChange={handleTextbookUpload}
                disabled={uploading}
                className="block w-full max-w-md text-sm text-primary file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:bg-accent-blue file:text-white file:font-medium disabled:opacity-60"
              />
              {uploading && <p className="mt-2 text-sm text-primary/70">Uploading PDF…</p>}
            </div>
          )}
          {textbookMode === "existing" && textbooks.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-primary/90 mb-2">Select textbook</label>
              <select
                value={selectedTextbook}
                onChange={(e) => setSelectedTextbook(e.target.value)}
                className="w-full max-w-md px-4 py-2 rounded-lg border border-glass-border bg-surface-light text-primary"
              >
                <option value="">— Select —</option>
                {textbooks.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-primary/90 mb-2">
              Chapter or topic (optional)
            </label>
            <input
              type="text"
              value={chapterInput}
              onChange={(e) => setChapterInput(e.target.value)}
              placeholder="e.g. Chapter 5 – Cell Biology"
              className="w-full max-w-md px-4 py-2 rounded-lg border border-glass-border bg-surface-light text-primary placeholder:text-primary/50"
            />
          </div>
        </div>
      )}

      {tab === "weblink" && (
        <div>
          <label className="block text-sm font-medium text-primary/90 mb-2">Site URL</label>
          <input
            type="url"
            value={weblinkUrl}
            onChange={(e) => setWeblinkUrl(e.target.value)}
            placeholder="https://example.com/article"
            className="w-full max-w-md px-4 py-2 rounded-lg border border-glass-border bg-surface-light text-primary placeholder:text-primary/50"
          />
        </div>
      )}

      {tab === "files" && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-primary/90 mb-2">
              Upload files (txt, pdf, ppt)
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.pdf,.ppt,.pptx"
              multiple
              onChange={addFiles}
              className="block w-full max-w-md text-sm text-primary file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:bg-accent-blue file:text-white file:font-medium"
            />
          </div>
          {files.length > 0 && (
            <ul className="space-y-1">
              {files.map((f, i) => (
                <li key={i} className="flex items-center gap-2 text-sm text-primary">
                  <span className="truncate">{f.name}</span>
                  <button
                    type="button"
                    onClick={() => removeFile(i)}
                    className="text-red-400 hover:text-red-300"
                    aria-label="Remove"
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-primary/90 mb-2">
          Number of flashcards: {count}
        </label>
        <input
          type="range"
          min={5}
          max={35}
          value={count}
          onChange={(e) => onCountChange(Number(e.target.value))}
          className="w-full max-w-xs h-2 rounded-full appearance-none bg-surface-light border border-glass-border accent-accent-blue"
        />
      </div>

      {error && <p className="text-sm text-red-400" role="alert">{error}</p>}

      <LoadingSpinner loading={loading} message="Generating flashcards...">
        <button
          type="button"
          onClick={handleGenerate}
          disabled={loading}
          className="px-5 py-2.5 rounded-xl font-medium text-deep bg-accent-blue hover:bg-accent-blue/90 focus:outline-none focus:ring-2 focus:ring-accent-blue disabled:opacity-60"
        >
          Generate Flashcards
        </button>
      </LoadingSpinner>
    </div>
  );
}
