import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

export interface Teacher {
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

interface TeacherContextValue {
  teacher: Teacher | null;
  setTeacher: (t: Teacher | null) => void;
  completeOnboarding: (data: Teacher) => void;
  logout: () => void;
}

const TeacherContext = createContext<TeacherContextValue | null>(null);

export function TeacherProvider({ children }: { children: React.ReactNode }) {
  const [teacher, setTeacherState] = useState<Teacher | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as Teacher;
        setTeacherState(parsed);
      }
    } catch {
      // ignore
    }
  }, []);

  const setTeacher = useCallback((t: Teacher | null) => {
    setTeacherState(t);
    if (t) localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
    else localStorage.removeItem(STORAGE_KEY);
  }, []);

  const completeOnboarding = useCallback((data: Teacher) => {
    setTeacherState(data);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }, []);

  const logout = useCallback(() => {
    setTeacherState(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return (
    <TeacherContext.Provider value={{ teacher, setTeacher, completeOnboarding, logout }}>
      {children}
    </TeacherContext.Provider>
  );
}

export function useTeacher() {
  const ctx = useContext(TeacherContext);
  if (!ctx) throw new Error('useTeacher must be used within TeacherProvider');
  return ctx;
}
