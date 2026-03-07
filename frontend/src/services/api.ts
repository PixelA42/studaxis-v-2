/**
 * Studaxis API client — frontend-to-backend integration layer.
 * All requests go to the local FastAPI server (API bridge).
 * Uses relative /api so it works when served from same origin (prod) or via Vite proxy (dev).
 */
const API_BASE = "";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };
  if (!isFormData) headers["Content-Type"] = "application/json";
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const raw = await res.text();
    let message = raw || `API error ${res.status}`;
    try {
      const json = JSON.parse(raw) as { detail?: string };
      if (typeof json.detail === "string") message = json.detail;
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
  topic?: string;
  user_query?: string | null;
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

/** Chat request/response (POST /api/chat) */
export interface ChatRequest {
  message: string;
  is_clarification?: boolean;
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
}

/** Auth response (signup/login) — JWT + user info */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  email: string;
}

/** Auth response (signup/login) — JWT + user info */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  email: string;
}

/** User profile (AuthContext — matches backend /api/user/profile) */
export interface UserProfile {
  profile_name: string | null;
  profile_mode: "solo" | "teacher_linked" | "teacher_linked_provisional" | null;
  class_code: string | null;
  user_role: "student" | "teacher" | null;
}

/** Auth response (signup/login) — JWT + user info */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  email: string;
}

/** Auth response (signup/login) — JWT + user info */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  email: string;
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
      context: params.context ?? undefined,
    }),
  });
}

/**
 * Get user progress, streaks, preferences (same schema as Streamlit).
 */
export async function getUserStats(): Promise<UserStats> {
  return request<UserStats>("/api/user/stats");
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
  textbooks: Array<{ id: string; name: string }>;
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
 * Upload a PDF textbook to sample_textbooks.
 */
export async function uploadTextbook(file: File): Promise<TextbookUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/textbooks/upload`, {
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
  return res.json() as Promise<TextbookUploadResponse>;
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
  const res = await fetch(`${API_BASE}/api/flashcards/generate/files`, {
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
      topic: params.topic ?? "General",
      user_query: params.user_query ?? null,
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
 * Fetch all stored flashcards.
 */
export async function getFlashcards(): Promise<FlashcardsListResponse> {
  return request<FlashcardsListResponse>("/api/flashcards");
}

/**
 * Fetch cards due for review (next_review <= now or missing).
 */
export async function getFlashcardsDue(): Promise<FlashcardsListResponse> {
  return request<FlashcardsListResponse>("/api/flashcards/due");
}

/**
 * Append cards to storage (enriched with next_review, etc.).
 */
export async function postFlashcards(
  cards: FlashcardItem[]
): Promise<{ ok: boolean; appended: number }> {
  return request<{ ok: boolean; appended: number }>("/api/flashcards", {
    method: "POST",
    body: JSON.stringify({ cards }),
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

// ——— Quiz & Grading ———

export interface QuizItem {
  id: string;
  topic: string;
  question: string;
  expected_answer?: string;
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
  answers: Array<{ question_id: string; answer: string }>;
}

export interface QuizSubmitResult {
  question_id: string;
  score?: number;
  feedback?: string;
  error?: string;
}

export interface QuizSubmitResponse {
  results: QuizSubmitResult[];
  quiz_stats_updated: boolean;
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
 */
export async function postQuizSubmit(
  quizId: string,
  params: QuizSubmitRequest
): Promise<QuizSubmitResponse> {
  return request<QuizSubmitResponse>(
    `/api/quiz/${encodeURIComponent(quizId)}/submit`,
    {
      method: "POST",
      body: JSON.stringify({ answers: params.answers }),
    }
  );
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
