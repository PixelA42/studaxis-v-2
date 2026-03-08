/**
 * Teacher Dashboard API — backend integration for onboarding and class management.
 * Uses VITE_TEACHER_BACKEND_URL (e.g. main FastAPI backend).
 */

export interface TeacherOnboardPayload {
  name: string;
  email: string;
  subject: string;
  grade: string;
  school: string;
  city: string;
  board: string;
  className: string;
  classCode: string;
  numStudents: string;
}

/**
 * POST /api/teacher/onboard — register teacher + create first class.
 * Persists to backend data/teachers/{class_code}.json.
 * No auth required (public onboarding).
 */
export async function postTeacherOnboard(payload: TeacherOnboardPayload): Promise<{ ok: boolean; classCode: string }> {
  const base = import.meta.env.VITE_TEACHER_BACKEND_URL;
  if (!base?.trim()) {
    return { ok: false, classCode: payload.classCode };
  }
  const url = `${base.replace(/\/$/, '')}/api/teacher/onboard`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Teacher onboard failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
