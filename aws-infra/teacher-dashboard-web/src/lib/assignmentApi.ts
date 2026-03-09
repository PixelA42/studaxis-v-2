/**
 * Assignment API — teacher creates and manages assignments
 * Students fetch their assignments via class_code
 */

import { getAuthHeaders } from './teacherApi';

const getBase = () => (import.meta.env.VITE_API_GATEWAY_URL || '').replace(/\/$/, '');

export interface Assignment {
  assignment_id: string;
  teacher_id: string;
  class_code: string;
  content_type: 'quiz' | 'notes';
  content_id: string;
  title: string;
  description?: string;
  due_date?: string;
  created_at: string;
  status: 'active' | 'deleted';
  completed?: boolean;
  completed_at?: string;
  content_data?: any;
}

export interface CreateAssignmentPayload {
  teacher_id: string;
  class_code: string;
  content_type: 'quiz' | 'notes';
  content_id: string;
  title: string;
  description?: string;
  due_date?: string;
  content_data?: any;
}

/**
 * POST /assignments — create new assignment
 */
export async function createAssignment(payload: CreateAssignmentPayload): Promise<Assignment> {
  const base = getBase();
  if (!base?.trim()) throw new Error('VITE_API_GATEWAY_URL not configured');
  
  const url = `${base}/assignments`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(payload),
  });
  
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `Create assignment failed: ${res.status}`);
  }
  
  return res.json();
}

/**
 * GET /assignments?class_code=X — list assignments for a class
 */
export async function listAssignmentsForClass(classCode: string, teacherId?: string): Promise<Assignment[]> {
  const base = getBase();
  if (!base?.trim()) return [];
  
  let url = `${base}/assignments?class_code=${encodeURIComponent(classCode)}`;
  if (teacherId) {
    url += `&teacher_id=${encodeURIComponent(teacherId)}`;
  }
  
  const res = await fetch(url, { headers: getAuthHeaders() });
  if (!res.ok) return [];
  
  const data = await res.json();
  return data.assignments ?? [];
}

/**
 * GET /assignments/student?user_id=X&class_code=Y — get student's assignments
 */
export async function getStudentAssignments(userId: string, classCode: string): Promise<Assignment[]> {
  const base = getBase();
  if (!base?.trim()) return [];
  
  const url = `${base}/assignments/student?user_id=${encodeURIComponent(userId)}&class_code=${encodeURIComponent(classCode)}`;
  const res = await fetch(url, { headers: getAuthHeaders() });
  
  if (!res.ok) return [];
  
  const data = await res.json();
  return data.assignments ?? [];
}

/**
 * POST /assignments/complete — mark assignment as completed
 */
export async function markAssignmentComplete(userId: string, assignmentId: string, score?: number): Promise<any> {
  const base = getBase();
  if (!base?.trim()) throw new Error('VITE_API_GATEWAY_URL not configured');
  
  const url = `${base}/assignments/complete`;
  const body: any = { user_id: userId, assignment_id: assignmentId };
  if (score !== undefined) body.score = score;
  
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(body),
  });
  
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `Mark complete failed: ${res.status}`);
  }
  
  return res.json();
}

/**
 * DELETE /assignments/{id} — delete assignment
 */
export async function deleteAssignment(assignmentId: string, teacherId: string): Promise<any> {
  const base = getBase();
  if (!base?.trim()) throw new Error('VITE_API_GATEWAY_URL not configured');
  
  const url = `${base}/assignments/${assignmentId}`;
  const res = await fetch(url, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ teacher_id: teacherId }),
  });
  
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `Delete assignment failed: ${res.status}`);
  }
  
  return res.json();
}
