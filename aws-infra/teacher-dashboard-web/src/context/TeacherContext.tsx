import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

export interface Teacher {
  teacherId?: string;
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

const STORAGE_KEY = 'studaxis_teacher';
/** JWT storage key — shared with teacherApi for Authorization header */
export const TEACHER_TOKEN_KEY = 'studaxis_teacher_token';

interface TeacherContextValue {
  teacher: Teacher | null;
  token: string | null;
  setTeacher: (t: Teacher | null) => void;
  completeOnboarding: (data: Teacher, options?: { token?: string }) => void;
  logout: () => void;
}

const TeacherContext = createContext<TeacherContextValue | null>(null);

export function TeacherProvider({ children }: { children: React.ReactNode }) {
  const [teacher, setTeacherState] = useState<Teacher | null>(null);
  const [token, setTokenState] = useState<string | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      const savedToken = localStorage.getItem(TEACHER_TOKEN_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as Teacher;
        setTeacherState(parsed);
      }
      if (savedToken) setTokenState(savedToken);
    } catch {
      // ignore
    }
  }, []);

  const setTeacher = useCallback((t: Teacher | null) => {
    setTeacherState(t);
    if (t) localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
    else localStorage.removeItem(STORAGE_KEY);
  }, []);

  const completeOnboarding = useCallback((data: Teacher, options?: { token?: string }) => {
    setTeacherState(data);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    if (options?.token) {
      setTokenState(options.token);
      localStorage.setItem(TEACHER_TOKEN_KEY, options.token);
    }
  }, []);

  const logout = useCallback(() => {
    setTeacherState(null);
    setTokenState(null);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(TEACHER_TOKEN_KEY);
  }, []);

  return (
    <TeacherContext.Provider value={{ teacher, token, setTeacher, completeOnboarding, logout }}>
      {children}
    </TeacherContext.Provider>
  );
}

export function useTeacher() {
  const ctx = useContext(TeacherContext);
  if (!ctx) throw new Error('useTeacher must be used within TeacherProvider');
  return ctx;
}
