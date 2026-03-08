/**
 * AppSync GraphQL client for teacher dashboard
 * Uses API key auth (MVP); Cognito/IAM in Phase 2
 */

const ENDPOINT = import.meta.env.VITE_APPSYNC_ENDPOINT || '';
const API_KEY = import.meta.env.VITE_APPSYNC_API_KEY || '';

export interface StudentProgress {
  user_id: string;
  class_code?: string | null;
  current_streak: number;
  device_id?: string | null;
  last_quiz_date?: string | null;
  last_sync_timestamp: string;
}

export interface ListStudentProgressesResponse {
  data?: {
    listStudentProgresses?: {
      items?: StudentProgress[] | null;
      nextToken?: string | null;
    } | null;
  };
  errors?: Array<{ message: string }>;
}

/**
 * Fetch student progress from AppSync, filtered by class_code at the API level.
 * Teachers pass their classCode; backend returns only students in that class.
 * Solo learners (class_code=SOLO) are never returned.
 */
export async function listStudentProgresses(classCode: string): Promise<StudentProgress[]> {
  if (!ENDPOINT || !API_KEY) {
    console.warn('AppSync not configured: VITE_APPSYNC_ENDPOINT or VITE_APPSYNC_API_KEY missing');
    return [];
  }

  const query = `
    query ListStudentProgresses($class_code: String, $limit: Int, $nextToken: String) {
      listStudentProgresses(class_code: $class_code, limit: $limit, nextToken: $nextToken) {
        items {
          user_id
          class_code
          current_streak
          device_id
          last_quiz_date
          last_sync_timestamp
        }
        nextToken
      }
    }
  `;

  const variables: Record<string, unknown> = {
    class_code: classCode?.trim() || null,
    limit: 100,
  };

  const res = await fetch(ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': API_KEY,
    },
    body: JSON.stringify({ query, variables }),
  });

  if (!res.ok) {
    throw new Error(`AppSync request failed: ${res.status} ${res.statusText}`);
  }

  const json = (await res.json()) as ListStudentProgressesResponse;
  if (json.errors?.length) {
    throw new Error(json.errors.map((e) => e.message).join('; '));
  }

  const items = json.data?.listStudentProgresses?.items ?? [];
  return items.filter(Boolean) as StudentProgress[];
}

/**
 * Optional: Trigger sync on teacher backend (e.g. POST /api/sync).
 * Set VITE_TEACHER_BACKEND_URL to enable. Fire-and-forget; does not block.
 */
export async function triggerBackendSyncIfConfigured(): Promise<void> {
  const base = import.meta.env.VITE_TEACHER_BACKEND_URL;
  if (!base?.trim()) return;
  try {
    await fetch(`${base.replace(/\/$/, '')}/api/sync`, { method: 'POST' });
  } catch {
    // Ignore — teacher dashboard primarily refreshes from AppSync
  }
}

/**
 * Check AppSync connectivity and return sync status.
 * Used by CloudSyncStatus and SyncStatus page.
 * Does a lightweight listStudentProgresses query to verify reachability.
 */
export async function checkAppSyncConnectivity(classCode: string): Promise<{
  ok: boolean;
  lastSyncTimestamp: string | null;
  error?: string;
}> {
  if (!ENDPOINT || !API_KEY) {
    return {
      ok: false,
      lastSyncTimestamp: null,
      error: 'AppSync not configured',
    };
  }

  try {
    await listStudentProgresses(classCode || '');
    return {
      ok: true,
      lastSyncTimestamp: new Date().toISOString(),
    };
  } catch (e) {
    return {
      ok: false,
      lastSyncTimestamp: null,
      error: e instanceof Error ? e.message : 'Connection failed',
    };
  }
}
