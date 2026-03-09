/**
 * Teacher Dashboard API — backend integration for onboarding and class management.
 * Uses VITE_TEACHER_BACKEND_URL (e.g. main FastAPI backend).
 * JWT from teacherLogin is stored in localStorage and attached via Authorization header.
 */

import type { Teacher } from '../context/TeacherContext';
import { TEACHER_TOKEN_KEY } from '../context/TeacherContext';

const getBase = () => (import.meta.env.VITE_TEACHER_BACKEND_URL || '').replace(/\/$/, '');

/** Get Authorization header for authenticated requests. */
export function getAuthHeaders(): Record<string, string> {
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem(TEACHER_TOKEN_KEY) : null;
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export interface TeacherAuthResponse {
  access_token: string;
  token_type: string;
  teacher: Teacher;
}

/**
 * POST /api/teacher/auth — authenticate by classCode (+ optional teacherId).
 * Matches exact Login UI fields. Returns JWT + teacher. Save token to localStorage after success.
 */
export async function teacherLogin(
  classCode: string,
  teacherId?: string | null
): Promise<TeacherAuthResponse> {
  const base = getBase();
  if (!base?.trim()) throw new Error('VITE_TEACHER_BACKEND_URL not configured');
  const cc = (classCode || '').trim().toUpperCase();
  if (cc.length < 3) throw new Error('classCode is required (min 3 chars)');
  const url = `${base}/api/teacher/auth`;
  const body: { classCode: string; teacherId?: string } = { classCode: cc };
  if (teacherId?.trim()) body.teacherId = teacherId.trim();
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Login failed: ${res.status}`);
  }
  return res.json();
}

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
 * GET /api/teacher/lookup?classCode=XXX — fetch teacher by class code.
 * Used by Login for returning teachers. Returns teacher object or null if not found.
 */
export async function getTeacherByClassCode(classCode: string): Promise<Teacher | null> {
  const base = getBase();
  if (!base?.trim()) return null;
  const cc = (classCode || '').trim().toUpperCase();
  if (cc.length < 3) return null;
  const url = `${base}/api/teacher/lookup?classCode=${encodeURIComponent(cc)}`;
  const res = await fetch(url, { headers: getAuthHeaders() });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Teacher lookup failed: ${res.status} ${res.statusText}`);
  const data = await res.json();
  return {
    teacherId: data.teacherId || data.classCode,
    name: data.name || '',
    email: data.email || '',
    subject: data.subject || '',
    grade: data.grade || '',
    school: data.school || '',
    city: data.city || '',
    board: data.board || '',
    className: data.className || '',
    classCode: data.classCode || cc,
    numStudents: data.numStudents || '',
  } as Teacher;
}

// ═════════════════════════════════════════════════════════════════════════
// Class Manager API (multi-class management via Lambda)
// Uses VITE_API_GATEWAY_URL — POST/GET /classes, GET /classes/verify
// ═════════════════════════════════════════════════════════════════════════

const getApiGatewayBase = () => (import.meta.env.VITE_API_GATEWAY_URL || '').replace(/\/$/, '');

export interface StudaxisClass {
  class_id: string;
  teacher_id: string;
  class_name: string;
  class_code: string;
  created_at?: string;
}

export async function createClass(teacherId: string, className: string): Promise<StudaxisClass> {
  const base = getApiGatewayBase();
  if (!base?.trim()) throw new Error('VITE_API_GATEWAY_URL not configured');
  const url = `${base}/classes`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ teacher_id: teacherId, class_name: className }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `Create class failed: ${res.status}`);
  }
  return res.json();
}

export async function getClassesForTeacher(teacherId: string): Promise<StudaxisClass[]> {
  const base = getApiGatewayBase();
  if (!base?.trim()) return [];
  const url = `${base}/classes?teacher_id=${encodeURIComponent(teacherId)}`;
  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) return [];
  const data = await res.json();
  return data.classes ?? [];
}

export async function verifyClassCode(classCode: string): Promise<{ class_id: string; class_name: string; class_code: string } | null> {
  const base = getApiGatewayBase();
  if (!base?.trim()) return null;
  const code = (classCode || '').trim().toUpperCase();
  if (code.length < 4) return null;
  const url = `${base}/classes/verify?code=${encodeURIComponent(code)}`;
  const res = await fetch(url);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Verify failed: ${res.status}`);
  return res.json();
}

// ═════════════════════════════════════════════════════════════════════════
// Onboarding
// ═════════════════════════════════════════════════════════════════════════

/**
 * POST /api/teacher/onboard — register teacher + create first class.
 * Persists to backend data/teachers/{class_code}.json.
 * No auth required (public onboarding).
 */
export async function postTeacherOnboard(payload: TeacherOnboardPayload): Promise<{ ok: boolean; classCode: string }> {
  const base = getBase();
  if (!base?.trim()) {
    return { ok: false, classCode: payload.classCode };
  }
  const url = `${base}/api/teacher/onboard`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Teacher onboard failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
