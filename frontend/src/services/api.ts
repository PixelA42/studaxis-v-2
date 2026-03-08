/**
 * Studaxis API client — frontend-to-backend integration layer.
 * All requests go to the local FastAPI server (API bridge).
 * Uses relative /api so it works when served from same origin (prod) or via Vite proxy (dev).
 * Attaches JWT from localStorage to Authorization header; on 401, triggers logout + redirect.
 */
const API_BASE = "";
const STORAGE_TOKEN = "studaxis_token";

let onUnauthorized: (() => void) | null = null;

/** Register handler for 401 responses. AuthContext calls this with logout + redirect. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

const API_TIMEOUT_MS = 25000; // Offline-first: avoid infinite spinners when backend unreachable

async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const url = `${API_BASE}${path}`;
  const isFormData = options.body instanceof FormData;
  const headers = new Headers(options.headers as HeadersInit);
  if (!isFormData) headers.set("Content-Type", "application/json");
  const token = localStorage.getItem(STORAGE_TOKEN);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  const res = await fetch(url, { ...options, headers, signal: controller.signal }).finally(() =>
    clearTimeout(timeoutId)
  );
  if (res.status === 401) {
    if (token) onUnauthorized?.();
    throw new Error("Unauthorized");
  }
  return res;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, options);
  if (!res.ok) {
    const raw = await res.text();
    let message = raw || `API error ${res.status}`;
    try {
      const json = JSON.parse(raw) as { detail?: string | Array<{ loc?: (string | number)[]; msg?: string }> };
      if (typeof json.detail === "string") {
        message = json.detail;
      } else if (Array.isArray(json.detail) && json.detail.length > 0) {
        const first = json.detail[0];
        const msg = first?.msg ?? first?.loc?.join(" ") ?? JSON.stringify(json.detail);
        message = typeof msg === "string" ? msg : JSON.stringify(msg);
      }
    } catch {
      // keep raw message
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

// ——— Types (match FastAPI Pydantic models) ———

export interface FlashcardItem {
  id: string;
  topic: string;
  front: string;
  back: string;
  /** Optional: textbook | weblink | file */
  sourceType?: string | string[];
  /** Optional storage/SRS fields (next_review ISO, interval days, etc.) */
  next_review?: string;
  interval?: number;
  repetitions?: number;
  ease_factor?: number;
  question?: string;
  answer?: string;
}

export interface FlashcardGenerateRequest {
  topic_or_chapter: string;
  input_type?: "Topic Name" | "Textbook Chapter";
  count?: number;
  offline_mode?: boolean;
  user_id?: string | null;
}

export interface FlashcardGenerateResponse {
  cards: FlashcardItem[];
  topic: string;
}

export interface FlashcardExplainRequest {
  front: string;
  back: string;
  subject?: string;
  difficulty?: string;
}

export interface FlashcardExplainResponse {
  text: string;
  confidence_score: number;
}

export interface StudyRecommendationRequest {
  topic: string;
  time_budget_minutes?: number;
  review_mode?: string | null;
  user_id?: string | null;
  offline_mode?: boolean;
}

export interface StudyRecommendationResponse {
  text: string;
  confidence_score: number;
}

export interface HealthResponse {
  status: string;
  service: string;
  ollama_available?: boolean;
}

/** Auth: signup/login response with JWT */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  email: string;
  onboarding_complete?: boolean;
}

/** Hardware check (Phase 8): ok / warn / block + specs + tips */
export interface HardwareResponse {
  status: "ok" | "warn" | "block";
  message: string;
  specs: {
    ram_gb?: number;
    ram_available_gb?: number;
    disk_free_gb?: number;
    cpu_count?: number;
    os?: string;
    [key: string]: unknown;
  };
  tips: string[];
  quantization_recommendation?: string;
  min_ram_gb?: number;
  min_disk_gb?: number;
  recommended_ram_gb?: number;
  error?: string;
}

/**
 * Hardware check for boot flow. Returns status (ok/warn/block), specs, and optimization tips.
 */
export async function getHardware(): Promise<HardwareResponse> {
  return request<HardwareResponse>("/api/hardware");
}

/** Task types for AI chat (maps to backend AITaskType) */
export type ChatTaskType =
  | "chat"
  | "clarify"
  | "explain_topic"
  | "quiz_me"
  | "flashcards"
  | "step_by_step";

/** Chat request/response (POST /api/chat) */
export interface ChatRequest {
  message: string;
  is_clarification?: boolean;
  task_type?: ChatTaskType;
  subject?: string;
  textbook_id?: string | null;
  context?: {
    difficulty?: string;
    chat_history?: Array<{ role: string; content: string }>;
    subject?: string;
    active_textbook?: string;
    user_id?: string | null;
  };
}

export interface ChatResponse {
  text: string;
  confidence_score: number;
  metadata?: Record<string, unknown>;
}

/** Single chat message (stored in user_stats.chat_history) */
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  is_clarification?: boolean;
  parent_idx?: number | null;
}

/** Auth response (signup/login) — JWT + user info */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  email: string;
  onboarding_complete?: boolean;
}

/** Auth response (signup/login) — JWT + user info */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  email: string;
  onboarding_complete?: boolean;
}

/** Auth response (signup/login) — JWT + user info */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  email: string;
  onboarding_complete?: boolean;
}

/** User profile (AuthContext — matches backend /api/user/profile) */
export interface UserProfile {
  profile_name: string | null;
  profile_mode: "solo" | "teacher_linked" | "teacher_linked_provisional" | null;
  class_code: string | null;
  user_role: "student" | "teacher" | null;
  onboarding_complete?: boolean;
}

/** Auth response (signup/login) — JWT + user info */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  email: string;
  onboarding_complete?: boolean;
}

/** Auth response (signup/login) — JWT + user info */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  email: string;
  onboarding_complete?: boolean;
}

/** User stats (same schema as backend /api/user/stats) */
export interface UserStats {
  user_id?: string;
  last_sync_timestamp?: string | null;
  streak?: { current?: number; longest?: number; last_activity_date?: string | null };
  quiz_stats?: {
    total_attempted?: number;
    total_correct?: number;
    average_score?: number;
    last_quiz_date?: string | null;
    by_topic?: Record<string, { attempts?: number; avg_score?: number }>;
  };
  flashcard_stats?: { total_reviewed?: number; mastered?: number; due_for_review?: number };
  chat_history?: ChatMessage[];
  preferences?: {
    difficulty_level?: string;
    theme?: "light" | "dark";
    language?: string;
    sync_enabled?: boolean;
    subject?: string;
    grade?: string;
  };
  hardware_info?: Record<string, unknown>;
}

/** Auth response (signup/login): JWT + user info */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  email: string;
}

// ——— API functions ———

/**
 * Turn-based chat with local LLM. Supports clarification follow-ups.
 */
export async function postChat(params: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      message: params.message,
      is_clarification: params.is_clarification ?? false,
      task_type: params.task_type ?? "chat",
      subject: params.subject ?? undefined,
      textbook_id: params.textbook_id ?? undefined,
      context: params.context ?? undefined,
    }),
  });
}

/** Chat history session (Layer 2 persistence) */
export interface ChatHistorySession {
  id: string;
  title: string;
  messages: ChatMessage[];
  timestamp: string;
  subject: string;
}

/** Fetch chat history from backend (restore when localStorage is empty). */
export async function fetchChatHistory(): Promise<ChatHistorySession[]> {
  return request<ChatHistorySession[]>("/api/chat/history");
}

/** Save a chat session to backend after New Chat. */
export async function saveChatHistoryToBackend(
  session: ChatHistorySession
): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/api/chat/history/save", {
    method: "POST",
    body: JSON.stringify(session),
  });
}

/**
 * Get user progress, streaks, preferences (same schema as Streamlit).
 */
export async function getUserStats(): Promise<UserStats> {
  return request<UserStats>("/api/user/stats");
}

/** Insight item from GET /api/insights */
export interface InsightItem {
  id: string;
  title: string;
  description: string;
  insight_type: string;
  priority: "high" | "medium" | "low";
  related_subject: string;
  suggested_action: string;
  weak_topic_name?: string;
  weak_topic_score?: number;
  mastery_pct?: number;
  trend_points?: number[];
}

/** Response from GET /api/insights */
export interface InsightsResponse {
  insights: InsightItem[];
  study_recommendation_text?: string;
}

/**
 * Fetch AI insights for the current user (weak topics, study recommendation, trends).
 * Auth-protected. Falls back to client-side build when offline or endpoint fails.
 */
export async function getInsights(): Promise<InsightsResponse> {
  return request<InsightsResponse>("/api/insights");
}

/**
 * Update user progress/preferences. Merges with existing on backend.
 */
export async function updateUserStats(stats: Partial<UserStats>): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/api/user/stats", {
    method: "PUT",
    body: JSON.stringify(stats),
  });
}

/** Current user from GET /api/user/me (auth-protected) */
export interface CurrentUserResponse {
  id: number;
  username: string;
  email: string;
}

/**
 * Get current authenticated user. Requires valid Bearer token.
 * Returns 401 if token is missing, expired, or invalid.
 */
export async function getCurrentUser(): Promise<CurrentUserResponse> {
  return request<CurrentUserResponse>("/api/user/me");
}

/**
 * Get persisted user profile from backend.
 */
export async function getUserProfile(): Promise<UserProfile> {
  return request<UserProfile>("/api/user/profile");
}

/**
 * Persist user profile to backend. Merges with existing.
 */
export async function postUserProfile(
  profile: Partial<UserProfile>
): Promise<UserProfile> {
  return request<UserProfile>("/api/user/profile", {
    method: "POST",
    body: JSON.stringify(profile),
  });
}

/**
 * Sign up a new user. Returns JWT on success.
 * Throws on validation error (422) or username/email already exists (409).
 */
export async function postSignup(params: {
  email: string;
  username: string;
  password: string;
}): Promise<AuthResponse> {
  return request<AuthResponse>("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/**
 * Log in with username or email + password. Returns JWT on success.
 * Throws on invalid credentials (401).
 */
export async function postLogin(params: {
  username_or_email: string;
  password: string;
}): Promise<AuthResponse> {
  return request<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/** Check if email is already registered. POST /api/auth/check-email */
export async function checkEmail(email: string): Promise<{ exists: boolean }> {
  return request<{ exists: boolean }>("/api/auth/check-email", {
    method: "POST",
    body: JSON.stringify({ email: email.trim().toLowerCase() }),
  });
}

/** Verify email via token from verification link. GET /api/auth/verify-email?token= */
export async function verifyEmail(token: string): Promise<{ message: string }> {
  return request<{ message: string }>(
    `/api/auth/verify-email?token=${encodeURIComponent(token)}`
  );
}

/** Request OTP for existing user. POST /api/auth/request-otp */
export async function postRequestOtp(params: { email: string }): Promise<{ message: string }> {
  return request<{ message: string }>("/api/auth/request-otp", {
    method: "POST",
    body: JSON.stringify({ email: params.email.trim().toLowerCase() }),
  });
}

/** Verify OTP, returns JWT. POST /api/auth/verify-otp */
export interface VerifyOtpResponse {
  access_token: string;
  token_type: string;
  onboarding_complete?: boolean;
}

export async function postVerifyOtp(params: {
  email: string;
  otp: string;
}): Promise<VerifyOtpResponse> {
  return request<VerifyOtpResponse>("/api/auth/verify-otp", {
    method: "POST",
    body: JSON.stringify({
      email: params.email.trim().toLowerCase(),
      otp: params.otp.replace(/\s/g, ""),
    }),
  });
}

/** Complete onboarding. POST /api/auth/complete-onboarding */
export interface CompleteOnboardingRequest {
  profile_name: string;
  role: "student" | "teacher";
  mode?: "solo" | "teacher_linked" | "teacher_linked_provisional";
  class_code?: string | null;
  subjects?: string | null;
  grade?: string | null;
}

export async function postCompleteOnboarding(
  body: CompleteOnboardingRequest
): Promise<{ ok: boolean; onboarding_complete: boolean }> {
  return request<{ ok: boolean; onboarding_complete: boolean }>(
    "/api/auth/complete-onboarding",
    {
      method: "POST",
      body: JSON.stringify(body),
    }
  );
}

/**
 * Health check — liveness/readiness of the FastAPI backend.
 */
export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

/**
 * Ping Ollama directly. Returns { ok: true } when local AI engine is responsive.
 * Used by loading screen to wait until Ollama is ready.
 */
export async function checkOllamaPing(): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/api/ollama/ping");
}

/** Response from GET /api/textbooks */
export interface TextbooksResponse {
  textbooks: Array<{
    id: string;
    name: string;
    filename?: string;
    subject?: string;
    uploaded_at?: string;
  }>;
}

/** Response from POST /api/textbooks/upload */
export interface TextbookUploadResponse {
  id: string;
  name: string;
}

/**
 * List textbooks from data/sample_textbooks (*.pdf, *.txt).
 */
export async function getTextbooks(): Promise<TextbooksResponse> {
  return request<TextbooksResponse>("/api/textbooks");
}

/**
 * Upload a PDF or PPTX textbook to sample_textbooks.
 */
export async function uploadTextbook(file: File): Promise<TextbookUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiFetch("/api/textbooks/upload", {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const raw = await res.text();
    let message = raw || `API error ${res.status}`;
    try {
      const json = JSON.parse(raw) as { detail?: string };
      if (typeof json.detail === "string") message = json.detail;
    } catch {
      // keep raw
    }
    console.error("[api] uploadTextbook failed:", res.status, message);
    throw new Error(message);
  }
  return res.json() as Promise<TextbookUploadResponse>;
}

/**
 * Upload a textbook with progress callback. Uses XHR for upload progress.
 * Supports PDF and PPTX. Same storage as Flashcards and AI Chat.
 */
export function uploadTextbookWithProgress(
  file: File,
  onProgress: (loaded: number, total: number) => void
): Promise<TextbookUploadResponse> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);
    const xhr = new XMLHttpRequest();
    const url = API_BASE ? `${API_BASE}/api/textbooks/upload` : "/api/textbooks/upload";
    const token = localStorage.getItem(STORAGE_TOKEN);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        onProgress(e.loaded, e.total);
      } else {
        onProgress(e.loaded, file.size);
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status === 401) {
        onUnauthorized?.();
        reject(new Error("Unauthorized"));
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const json = JSON.parse(xhr.responseText) as TextbookUploadResponse;
          resolve(json);
        } catch {
          reject(new Error("Invalid response"));
        }
      } else {
        let message = xhr.responseText || `API error ${xhr.status}`;
        try {
          const json = JSON.parse(xhr.responseText) as { detail?: string };
          if (typeof json.detail === "string") message = json.detail;
        } catch {
          // keep raw
        }
        console.error("[api] uploadTextbookWithProgress failed:", xhr.status, message);
        reject(new Error(message));
      }
    });

    xhr.addEventListener("error", () => {
      console.error("[api] uploadTextbookWithProgress network error");
      reject(new Error("Network error"));
    });
    xhr.addEventListener("abort", () => reject(new Error("Upload aborted")));

    xhr.open("POST", url);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.send(form);
  });
}

/** RAG search result chunk from embedded textbooks */
export interface RAGSearchResult {
  content: string;
  source?: string;
  subject?: string;
}

/** Response from GET /api/rag/search */
export interface RAGSearchResponse {
  results: RAGSearchResult[];
  message?: string;
}

/**
 * Semantic search over local ChromaDB. Returns top-k matching chunks from embedded textbooks.
 */
export async function ragSearch(q: string, k = 5): Promise<RAGSearchResponse> {
  const params = new URLSearchParams({ q: q.trim(), k: String(Math.min(Math.max(1, k), 20)) });
  return request<RAGSearchResponse>(`/api/rag/search?${params}`);
}

/**
 * Generate flashcards from a web URL. Fetches HTML, strips tags, sends to AI.
 */
export async function generateFlashcardsFromWeblink(params: {
  url: string;
  count: number;
}): Promise<FlashcardGenerateResponse> {
  return request<FlashcardGenerateResponse>("/api/flashcards/generate/weblink", {
    method: "POST",
    body: JSON.stringify({ url: params.url, count: params.count }),
  });
}

/** Generate from URL (topic-aware): POST /api/flashcards/generate-from-url */
export async function generateFlashcardsFromUrl(params: {
  url: string;
  subject: string;
  num_cards: number;
  difficulty?: string;
}): Promise<FlashcardGenerateResponse> {
  return request<FlashcardGenerateResponse>("/api/flashcards/generate-from-url", {
    method: "POST",
    body: JSON.stringify({
      url: params.url.trim(),
      subject: params.subject || "General",
      num_cards: params.num_cards,
      difficulty: params.difficulty ?? "Beginner",
    }),
  });
}

/** Generate from file (PDF/PPT only, topic-aware): POST /api/flashcards/generate-from-file */
export async function generateFlashcardsFromFile(params: {
  file: File;
  subject: string;
  num_cards: number;
}): Promise<FlashcardGenerateResponse> {
  const form = new FormData();
  form.append("file", params.file);
  form.append("subject", params.subject || "General");
  form.append("num_cards", String(params.num_cards));
  const res = await apiFetch("/api/flashcards/generate-from-file", {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const raw = await res.text();
    let message = raw || `API error ${res.status}`;
    try {
      const json = JSON.parse(raw) as { detail?: string };
      if (typeof json.detail === "string") message = json.detail;
    } catch {
      // keep raw
    }
    console.error("[api] generateFlashcardsFromFile failed:", res.status, message);
    throw new Error(message);
  }
  return res.json() as Promise<FlashcardGenerateResponse>;
}

/** Generate from pasted text (topic-aware): POST /api/flashcards/generate-from-text */
export async function generateFlashcardsFromText(params: {
  text: string;
  subject: string;
  num_cards: number;
  difficulty?: string;
}): Promise<FlashcardGenerateResponse> {
  return request<FlashcardGenerateResponse>("/api/flashcards/generate-from-text", {
    method: "POST",
    body: JSON.stringify({
      text: params.text.trim(),
      subject: params.subject || "General",
      num_cards: params.num_cards,
      difficulty: params.difficulty ?? "Beginner",
    }),
  });
}

/**
 * Generate flashcards from uploaded files (txt, pdf, ppt, pptx).
 */
export async function generateFlashcardsFromFiles(params: {
  files: File[];
  count: number;
}): Promise<FlashcardGenerateResponse> {
  const form = new FormData();
  params.files.forEach((f) => form.append("files", f));
  form.append("count", String(params.count));
  const res = await apiFetch("/api/flashcards/generate/files", {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const raw = await res.text();
    let message = raw || `API error ${res.status}`;
    try {
      const json = JSON.parse(raw) as { detail?: string };
      if (typeof json.detail === "string") message = json.detail;
    } catch {
      // keep raw
    }
    throw new Error(message);
  }
  return res.json() as Promise<FlashcardGenerateResponse>;
}

/**
 * Generate flashcards from a textbook by id (filename in sample_textbooks).
 * Falls back to topic-based generation if textbook content cannot be loaded.
 */
export async function generateFlashcardsFromTextbook(params: {
  textbook_id: string;
  chapter?: string;
  count: number;
}): Promise<FlashcardGenerateResponse> {
  return request<FlashcardGenerateResponse>("/api/flashcards/generate/textbook", {
    method: "POST",
    body: JSON.stringify({
      textbook_id: params.textbook_id,
      chapter: params.chapter ?? null,
      count: params.count,
    }),
  });
}

/**
 * Generate a deck of flashcards from a topic or chapter name (local AI).
 * Calls POST /api/flashcards/generate.
 */
export async function generateFlashcards(
  params: FlashcardGenerateRequest
): Promise<FlashcardGenerateResponse> {
  return request<FlashcardGenerateResponse>("/api/flashcards/generate", {
    method: "POST",
    body: JSON.stringify({
      topic_or_chapter: params.topic_or_chapter,
      input_type: params.input_type ?? "Topic Name",
      count: params.count ?? 10,
      offline_mode: params.offline_mode ?? true,
      user_id: params.user_id ?? null,
    }),
  });
}

/**
 * Get an AI explanation for a flashcard (front/back). Local LLM.
 * Calls POST /api/flashcards/explain.
 */
export async function explainFlashcard(
  params: FlashcardExplainRequest
): Promise<FlashcardExplainResponse> {
  return request<FlashcardExplainResponse>("/api/flashcards/explain", {
    method: "POST",
    body: JSON.stringify({
      front: params.front,
      back: params.back,
      subject: params.subject ?? "General",
      difficulty: params.difficulty ?? "Beginner",
    }),
  });
}

/**
 * Get a study plan / recommendation for a topic and time budget. Local AI.
 * Calls POST /api/study/recommendation.
 */
export async function getStudyRecommendation(
  params: StudyRecommendationRequest
): Promise<StudyRecommendationResponse> {
  return request<StudyRecommendationResponse>("/api/study/recommendation", {
    method: "POST",
    body: JSON.stringify({
      topic: params.topic,
      time_budget_minutes: params.time_budget_minutes ?? 15,
      review_mode: params.review_mode ?? "flashcards",
      user_id: params.user_id ?? null,
      offline_mode: params.offline_mode ?? true,
    }),
  });
}

/** Structured adaptive recommendation response */
export interface AdaptiveRecommendationResponse {
  weak_topic: string;
  suggested_action: string;
  difficulty_adjustment: string;
  text: string;
  confidence_score: number;
  has_data: boolean;
}

/** Adaptive flashcard recommendation: POST /api/flashcards/recommend.
 * Supports quiz-only mode when deck_id/subject are empty (uses quiz stats). */
export async function getFlashcardRecommendation(params: {
  deck_id?: string;
  subject?: string;
  hard_cards?: string[];
  easy_count?: number;
  hard_count?: number;
  difficulty?: string;
  insights?: { weak_subjects?: string[]; avg_quiz_score?: number; streak?: number };
}): Promise<AdaptiveRecommendationResponse> {
  return request<AdaptiveRecommendationResponse>("/api/flashcards/recommend", {
    method: "POST",
    body: JSON.stringify({
      deck_id: params.deck_id ?? "",
      subject: params.subject ?? "",
      hard_cards: params.hard_cards ?? [],
      easy_count: params.easy_count ?? 0,
      hard_count: params.hard_count ?? 0,
      difficulty: params.difficulty ?? "Beginner",
      insights: params.insights,
    }),
  });
}

/** Response from GET /api/flashcards and GET /api/flashcards/due */
export interface FlashcardsListResponse {
  cards: FlashcardItem[];
}

/** Dashboard flashcard format: conceptTitle, content, sourceType (textbook|weblink|semantics|file) */
export interface DashboardFlashcardItem {
  id: string;
  conceptTitle: string;
  content: string;
  sourceType?: string | string[];
}

export interface DashboardFlashcardsResponse {
  cards: DashboardFlashcardItem[];
}

/**
 * Fetch dashboard flashcards (concept cards for aerogel UI).
 * Maps stored flashcards to conceptTitle/content/sourceType format.
 */
export async function getDashboardFlashcards(): Promise<DashboardFlashcardsResponse> {
  return request<DashboardFlashcardsResponse>("/api/dashboard/flashcards");
}

/**
 * Fetch all stored flashcards (cards endpoint for backward compat).
 */
export async function getFlashcards(): Promise<FlashcardsListResponse> {
  return request<FlashcardsListResponse>("/api/flashcards/cards");
}

/**
 * Fetch all flashcard decks (new deck structure).
 */
export async function getFlashcardDecks(): Promise<{ decks: Array<Record<string, unknown>> }> {
  return request<{ decks: Array<Record<string, unknown>> }>("/api/flashcards");
}

/**
 * Fetch cards due for review (next_review <= now or missing).
 */
export async function getFlashcardsDue(): Promise<FlashcardsListResponse> {
  return request<FlashcardsListResponse>("/api/flashcards/due");
}

/**
 * Append cards to storage (enriched with next_review, etc.).
 * Optionally create/update a deck with deck_id.
 */
export async function postFlashcards(
  cards: FlashcardItem[],
  opts?: { deck_id?: string; deck_title?: string; deck_subject?: string }
): Promise<{ ok: boolean; appended: number }> {
  return request<{ ok: boolean; appended: number }>("/api/flashcards", {
    method: "POST",
    body: JSON.stringify({
      cards,
      deck_id: opts?.deck_id ?? undefined,
      deck_title: opts?.deck_title ?? undefined,
      deck_subject: opts?.deck_subject ?? undefined,
    }),
  });
}

/**
 * Replace stored flashcards (e.g. after marking easy/hard).
 */
export async function putFlashcards(
  cards: FlashcardItem[]
): Promise<{ ok: boolean; count: number }> {
  return request<{ ok: boolean; count: number }>("/api/flashcards", {
    method: "PUT",
    body: JSON.stringify({ cards }),
  });
}

/** POST /api/flashcards/deck - save full deck to backend (for recents sync) */
export async function postFlashcardDeck(deck: {
  id: string;
  title: string;
  subject: string;
  source?: string;
  card_count: number;
  easy_count: number;
  hard_count: number;
  cards: FlashcardItem[];
  created_at: string;
  last_studied: string;
}): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/api/flashcards/deck", {
    method: "POST",
    body: JSON.stringify(deck),
  });
}

/** PATCH /api/flashcards/review - update card ease and deck progress */
export async function patchFlashcardReview(params: {
  deck_id: string;
  card_id: string;
  ease: "easy" | "hard";
  next_review?: string;
}): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/api/flashcards/review", {
    method: "PATCH",
    body: JSON.stringify({
      deck_id: params.deck_id,
      card_id: params.card_id,
      ease: params.ease,
      next_review: params.next_review,
    }),
  });
}

// ——— Quiz & Grading ———

export interface QuizItem {
  id: string;
  topic?: string;
  question?: string;
  text?: string;
  expected_answer?: string;
  sample_answer?: string;
  rubric?: string;
  options?: string[];
  correct?: number;
  explanation?: string;
}

export interface QuizResponse {
  id: string;
  title: string;
  items: QuizItem[];
}

export interface GradeRequest {
  question_id: string;
  question: string;
  expected_answer?: string | null;
  topic?: string;
  answer: string;
  difficulty?: string;
  rubric?: string | null;
  user_id?: string | null;
  offline_mode?: boolean;
}

export interface GradeResponse {
  text: string;
  confidence_score: number;
  score?: number | null;
  metadata?: Record<string, unknown> | null;
}

export interface QuizSubmitRequest {
  answers: Array<{ question_id: string; answer?: string; user_answer?: string }>;
  /** Custom quiz items for panic mode when generated from material */
  items?: QuizItem[];
}

export interface QuizSubmitResult {
  question_id: string;
  score?: number;
  feedback?: string;
  error?: string;
}

export interface QuizSubmitResponse {
  score: number;
  max_score: number;
  percent: number;
  results: Array<{
    question_id: string;
    correct: boolean;
    score: number;
    correct_answer: string;
    explanation: string;
  }>;
  weak_topics_text?: string | null;
  recommendation_text?: string | null;
}

/**
 * Get quiz content by id (e.g. "quick" or "default").
 */
export async function getQuiz(quizId: string): Promise<QuizResponse> {
  return request<QuizResponse>(`/api/quiz/${encodeURIComponent(quizId)}`);
}

/**
 * Get quiz history (all past results).
 */
export async function getQuizHistory(): Promise<{ results: QuizResultItem[] }> {
  return request<{ results: QuizResultItem[] }>("/api/quiz/history");
}

/** Quiz result item from API */
export interface QuizResultItem {
  quiz_id: string;
  completed_at: string;
  score: number;
  max_score: number;
  percent: number;
  subject: string;
  question_type?: string;
  answers?: Array<{
    question_id: string;
    user_answer: string;
    correct: boolean;
    score: number;
    feedback?: string;
  }>;
}

/**
 * Grade a single answer (AI feedback). Does not update user stats; use quiz submit for that.
 */
export async function postGrade(params: GradeRequest): Promise<GradeResponse> {
  return request<GradeResponse>("/api/grade", {
    method: "POST",
    body: JSON.stringify({
      question_id: params.question_id,
      question: params.question,
      expected_answer: params.expected_answer ?? null,
      topic: params.topic ?? "General",
      answer: params.answer,
      difficulty: params.difficulty ?? "Beginner",
      rubric: params.rubric ?? null,
      user_id: params.user_id ?? null,
      offline_mode: params.offline_mode ?? true,
    }),
  });
}

/**
 * Submit quiz answers; backend grades each via AI and updates user stats.
 * answers: [{ question_id, user_answer }] or [{ question_id, answer }]
 */
export async function postQuizSubmit(
  quizId: string,
  params: QuizSubmitRequest
): Promise<QuizSubmitResponse> {
  const answers = params.answers.map((a) => ({
    question_id: a.question_id,
    user_answer: a.user_answer ?? a.answer ?? "",
  }));
  return request<QuizSubmitResponse>(
    `/api/quiz/${encodeURIComponent(quizId)}/submit`,
    {
      method: "POST",
      body: JSON.stringify({
        answers,
        ...(params.items && params.items.length > 0 ? { items: params.items } : {}),
      }),
    }
  );
}

/** Generate quiz from materials or topic. Returns { id, title, items } */
export async function postQuizGenerate(params: {
  source: "materials" | "topic";
  subject: string;
  source_ids?: string[] | null;
  topic_text?: string | null;
  question_type: "mcq" | "open_ended";
  num_questions: number;
  difficulty: string;
}): Promise<{ id: string; title: string; items: QuizItem[]; subject: string; difficulty: string; question_type: string }> {
  return request("/api/quiz/generate", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/** Generate quiz from URL. Returns { id, title, items } */
export async function postQuizGenerateFromUrl(params: {
  url: string;
  subject: string;
  topic_text?: string | null;
  num_questions: number;
  question_type: "mcq" | "open_ended";
  difficulty: string;
}): Promise<{ id: string; title: string; items: QuizItem[]; subject: string; difficulty: string; question_type: string }> {
  return request("/api/quiz/generate-from-url", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/** Generate quiz from pasted text. Returns { id, title, items } */
export async function postQuizGenerateFromText(params: {
  text: string;
  subject: string;
  topic_text?: string | null;
  num_questions: number;
  question_type: "mcq" | "open_ended";
  difficulty: string;
}): Promise<{ id: string; title: string; items: QuizItem[]; subject: string; difficulty: string; question_type: string }> {
  return request("/api/quiz/generate-from-text", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/** Generate quiz from uploaded file (PDF/PPT). Returns { id, title, items } */
export async function postQuizGenerateFromFile(params: {
  file: File;
  subject: string;
  topic_text?: string | null;
  num_questions: number;
  question_type: "mcq" | "open_ended";
  difficulty: string;
}): Promise<{ id: string; title: string; items: QuizItem[]; subject: string; difficulty: string; question_type: string }> {
  const form = new FormData();
  form.append("file", params.file);
  form.append("subject", params.subject);
  if (params.topic_text) form.append("topic_text", params.topic_text);
  form.append("num_questions", String(params.num_questions));
  form.append("question_type", params.question_type);
  form.append("difficulty", params.difficulty);
  const res = await apiFetch("/api/quiz/generate-from-file", {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const raw = await res.text();
    let message = raw || `API error ${res.status}`;
    try {
      const json = JSON.parse(raw) as { detail?: string };
      if (typeof json.detail === "string") message = json.detail;
    } catch {
      // keep raw
    }
    throw new Error(message);
  }
  return res.json();
}

/** Grade a single open-ended answer inline. Returns { score, feedback } */
export async function postQuizGradeAnswer(params: {
  question: string;
  user_answer: string;
  sample_answer: string;
  rubric: string;
  difficulty: string;
}): Promise<{ score: number; feedback: string }> {
  return request("/api/quiz/grade-answer", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/** Create flashcard deck from wrong quiz questions */
export async function postFlashcardsFromQuiz(params: {
  wrong_questions: Array<{ question_id?: string; text?: string; question?: string; correct_answer: string; explanation?: string }>;
}): Promise<{ ok: boolean; deck_id: string | null; card_count: number }> {
  return request("/api/flashcards/from-quiz", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/** Get assignments for class (teacher_linked students) */
export async function getStudentAssignments(classCode: string): Promise<
  Array<{ id: string; quiz_id: string; title: string; due_date: string; assigned_at: string; status: string }>
> {
  if (!classCode) return [];
  const params = new URLSearchParams({ class_code: classCode });
  return request(`/api/student/assignments?${params}`);
}

/** Mark assignment as completed */
export async function postAssignmentComplete(params: {
  assignment_id: string;
  score: number;
  completed_at?: string;
}): Promise<{ ok: boolean }> {
  return request("/api/student/assignment-complete", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/** Generate panic-mode questions from textbook. One subject only. */
export async function generatePanicQuizFromTextbook(params: {
  subject: string;
  textbook_id: string;
  chapter?: string;
  count?: number;
  question_type?: "mcq" | "open_ended";
}): Promise<QuizResponse & { question_type?: string }> {
  return request<QuizResponse & { question_type?: string }>(
    "/api/quiz/panic/generate/textbook",
    {
      method: "POST",
      body: JSON.stringify({
        subject: params.subject,
        textbook_id: params.textbook_id,
        chapter: params.chapter ?? null,
        count: params.count ?? 5,
        question_type: params.question_type ?? "open_ended",
      }),
    }
  );
}

/** Generate panic-mode questions from web URL. One subject only. */
export async function generatePanicQuizFromWeblink(params: {
  subject: string;
  url: string;
  count?: number;
  question_type?: "mcq" | "open_ended";
}): Promise<QuizResponse & { question_type?: string }> {
  return request<QuizResponse & { question_type?: string }>(
    "/api/quiz/panic/generate/weblink",
    {
      method: "POST",
      body: JSON.stringify({
        subject: params.subject,
        url: params.url,
        count: params.count ?? 5,
        question_type: params.question_type ?? "open_ended",
      }),
    }
  );
}

/** Generate panic-mode questions from uploaded files. One subject only. */
export async function generatePanicQuizFromFiles(params: {
  subject: string;
  files: File[];
  count?: number;
  question_type?: "mcq" | "open_ended";
}): Promise<QuizResponse & { question_type?: string }> {
  const form = new FormData();
  form.append("subject", params.subject);
  form.append("count", String(params.count ?? 5));
  form.append("question_type", params.question_type ?? "open_ended");
  params.files.forEach((f) => form.append("files", f));
  const res = await apiFetch("/api/quiz/panic/generate/files", {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const raw = await res.text();
    let message = raw || `API error ${res.status}`;
    try {
      const json = JSON.parse(raw) as { detail?: string };
      if (typeof json.detail === "string") message = json.detail;
    } catch {
      // keep raw
    }
    throw new Error(message);
  }
  return res.json() as Promise<QuizResponse & { question_type?: string }>;
}

/** Grade a single panic-mode question (open-ended inline feedback). POST /api/quiz/panic/grade-one */
export async function postPanicGradeOne(params: {
  question_id: string;
  question: string;
  answer: string;
  topic?: string;
  expected_answer?: string;
  question_type?: "mcq" | "open_ended";
  options?: string[];
  correct?: number;
}): Promise<{ question_id: string; score: number; feedback: string; topic?: string }> {
  return request("/api/quiz/panic/grade-one", {
    method: "POST",
    body: JSON.stringify({
      question_id: params.question_id,
      question: params.question,
      answer: params.answer,
      topic: params.topic ?? "General",
      expected_answer: params.expected_answer ?? "",
      question_type: params.question_type ?? "open_ended",
      options: params.options,
      correct: params.correct,
    }),
  });
}

// ——— Sync & Conflicts ———

/** Sync status: queue, connectivity, last sync */
export interface SyncStatusResponse {
  sync_enabled: boolean;
  last_sync_timestamp: string | null;
  online: boolean;
  queue: {
    total: number;
    quiz_attempts: number;
    streak_updates: number;
    oldest_item: string | null;
  };
}

/** Single conflict from orchestrator */
export interface SyncConflict {
  conflict_detected: boolean;
  entity_id: string;
  entity_type: string;
  reason: string;
  local_version?: number;
  cloud_version?: number;
  local_updated_at?: string;
  cloud_updated_at?: string;
  local_data?: Record<string, unknown>;
  cloud_data?: Record<string, unknown>;
  conflicting_fields?: string[];
  detected_at?: string;
}

/** Sync trigger — flush pending mutations via SyncManager */
export interface PostSyncResponse {
  ok: boolean;
  message?: string;
  synced?: number;
  failed?: number;
  pending?: number;
  online?: boolean;
  errors?: string[];
}

export async function getSyncStatus(): Promise<SyncStatusResponse> {
  return request<SyncStatusResponse>("/api/sync/status");
}

export async function postSync(): Promise<PostSyncResponse> {
  return request<PostSyncResponse>("/api/sync", {
    method: "POST",
  });
}

export async function getSyncConflicts(): Promise<{ conflicts: SyncConflict[]; message?: string }> {
  return request<{ conflicts: SyncConflict[]; message?: string }>("/api/sync/conflicts");
}

export async function resolveConflict(
  entityId: string,
  choice: "keep_local" | "keep_cloud" | "merge"
): Promise<{ ok: boolean; entity_id: string; choice: string }> {
  return request<{ ok: boolean; entity_id: string; choice: string }>(
    `/api/sync/conflicts/${encodeURIComponent(entityId)}/resolve`,
    {
      method: "POST",
      body: JSON.stringify({ choice }),
    }
  );
}

// ——— Diagnostics & Storage (Settings) ———

/** Diagnostics for Deployment Readiness panel */
export interface DiagnosticsResponse {
  app_version: string;
  environment: string;
  sync_enabled: boolean;
  sync_state: string;
  sync_readiness: string;
  last_sync_timestamp: string | null;
}

export async function getDiagnostics(): Promise<DiagnosticsResponse> {
  return request<DiagnosticsResponse>("/api/diagnostics");
}

/** Storage file item for Settings Storage panel */
export interface StorageFileItem {
  name: string;
  size_bytes: number;
  size_human: string;
  description: string;
}

export interface StorageFilesResponse {
  files: StorageFileItem[];
}

export async function getStorageFiles(): Promise<StorageFilesResponse> {
  return request<StorageFilesResponse>("/api/storage/files");
}

// ——— Data export & clear (Settings) ———

/** Export payload: user_stats, flashcards, profile */
export interface DataExportPayload {
  exported_at: string;
  version: string;
  user_stats: UserStats;
  flashcards: FlashcardItem[];
  profile: UserProfile;
}

/**
 * Export all user data as JSON. Returns the full payload for backup/migration.
 * Caller should trigger a file download (e.g. via blob URL).
 */
export async function getDataExport(): Promise<DataExportPayload> {
  return request<DataExportPayload>("/api/data/export");
}

/**
 * Clear local study data: reset user_stats, clear flashcards, reset profile.
 * Does NOT delete auth (user accounts remain). Requires confirmation in UI.
 */
export async function postDataClear(): Promise<{ ok: boolean; message?: string }> {
  return request<{ ok: boolean; message?: string }>("/api/data/clear", {
    method: "POST",
  });
}

// ——— Notifications ———

/** Notification item from backend */
export interface ApiNotification {
  id: string;
  type: string;
  title: string;
  message?: string;
  tag?: string;
  pinned?: boolean;
  read: boolean;
  timestamp: string;
  action?: { label: string; href: string };
}

/** GET /api/notifications — returns [] on 401/offline */
export async function getNotifications(): Promise<ApiNotification[]> {
  try {
    const res = await apiFetch("/api/notifications");
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : (data?.notifications ?? []);
  } catch {
    return [];
  }
}

/** POST /api/notifications/push */
export async function postNotificationPush(params: {
  type?: string;
  title: string;
  message?: string;
  tag?: string;
  pinned?: boolean;
  action?: { label: string; href: string };
}): Promise<ApiNotification> {
  return request<ApiNotification>("/api/notifications/push", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/** PATCH /api/notifications/{id}/read */
export async function patchNotificationRead(id: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/notifications/${encodeURIComponent(id)}/read`, {
    method: "PATCH",
  });
}

/** DELETE /api/notifications/{id} */
export async function deleteNotification(id: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/notifications/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

/** DELETE /api/notifications/all */
export async function deleteAllNotifications(): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/api/notifications/all", {
    method: "DELETE",
  });
}
