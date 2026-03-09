/**
 * ClassContext — multi-class management for teacher dashboard.
 * Holds classes[], activeClassId, activeClass (derived).
 * On login, fetches classes from API; if empty but teacher has classCode, uses legacy virtual class.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useTeacher } from './TeacherContext';
import { getClassesForTeacher, type StudaxisClass } from '../lib/teacherApi';

export type LegacyClass = { class_id: string; class_code: string; class_name: string; isLegacy: true };

export type ActiveClass = StudaxisClass | LegacyClass;

const ACTIVE_CLASS_STORAGE = 'studaxis_active_class_id';

interface ClassContextValue {
  classes: StudaxisClass[];
  activeClassId: string | null;
  activeClass: ActiveClass | null;
  setActiveClassId: (id: string | null) => void;
  refreshClasses: () => Promise<void>;
  isLoading: boolean;
}

const ClassContext = createContext<ClassContextValue | null>(null);

export function ClassProvider({ children }: { children: React.ReactNode }) {
  const { teacher } = useTeacher();
  const [classes, setClasses] = useState<StudaxisClass[]>([]);
  const [activeClassId, setActiveClassIdState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const teacherId = teacher?.teacherId || teacher?.classCode || '';

  const refreshClasses = useCallback(async () => {
    if (!teacherId) {
      setClasses([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    try {
      const list = await getClassesForTeacher(teacherId);
      setClasses(list);
      if (list.length === 0) {
        setActiveClassIdState(null);
      }
    } catch {
      setClasses([]);
    } finally {
      setIsLoading(false);
    }
  }, [teacherId]);

  useEffect(() => {
    refreshClasses();
  }, [refreshClasses]);

  // When classes load and we had a stored activeClassId, restore it if valid
  useEffect(() => {
    if (classes.length > 0 && !activeClassId) {
      const saved = typeof localStorage !== 'undefined' ? localStorage.getItem(ACTIVE_CLASS_STORAGE) : null;
      if (saved && classes.some((c) => c.class_id === saved)) {
        setActiveClassIdState(saved);
      } else {
        const first = classes[0];
        setActiveClassIdState(first.class_id);
        if (typeof localStorage !== 'undefined') localStorage.setItem(ACTIVE_CLASS_STORAGE, first.class_id);
      }
    }
  }, [classes, activeClassId]);

  const setActiveClassId = useCallback((id: string | null) => {
    setActiveClassIdState(id);
    if (typeof localStorage !== 'undefined') {
      if (id) localStorage.setItem(ACTIVE_CLASS_STORAGE, id);
      else localStorage.removeItem(ACTIVE_CLASS_STORAGE);
    }
  }, []);

  const activeClass: ActiveClass | null = (() => {
    if (classes.length > 0 && activeClassId) {
      const c = classes.find((x) => x.class_id === activeClassId);
      if (c) return c;
    }
    // Legacy: teacher has classCode but no classes in DynamoDB
    if (teacher?.classCode?.trim() && classes.length === 0) {
      return {
        class_id: teacher.classCode,
        class_code: teacher.classCode,
        class_name: teacher.className || teacher.classCode,
        isLegacy: true,
      } as LegacyClass;
    }
    return null;
  })();

  const value: ClassContextValue = {
    classes,
    activeClassId,
    activeClass,
    setActiveClassId,
    refreshClasses,
    isLoading,
  };

  return <ClassContext.Provider value={value}>{children}</ClassContext.Provider>;
}

export function useClass() {
  const ctx = useContext(ClassContext);
  if (!ctx) throw new Error('useClass must be used within ClassProvider');
  return ctx;
}
