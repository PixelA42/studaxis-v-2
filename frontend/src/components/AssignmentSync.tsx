/**
 * AssignmentSync — For teacher_linked users, fetches assignments on load and when online.
 * Pushes notification for each new assignment not in localStorage.
 */

import { useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useNotification } from "../contexts/NotificationContext";
import { getStudentAssignments } from "../services/api";
import {
  loadAssignmentsFromStorage,
  saveAssignmentsToStorage,
  type AssignmentItem,
} from "../services/storage";

export function AssignmentSync() {
  const { profile, connectivityStatus } = useAuth();
  const { push } = useNotification();

  useEffect(() => {
    if (profile.profile_mode !== "teacher_linked" || !profile.class_code) return;
    if (connectivityStatus !== "online") return;

    const run = async () => {
      try {
        const remote = await getStudentAssignments(profile.class_code ?? "");
        const local = loadAssignmentsFromStorage();
        const localIds = new Set(local.map((a) => a.id));
        const merged: AssignmentItem[] = [];

        for (const r of remote) {
          const a: AssignmentItem = {
            id: r.id,
            quiz_id: r.quiz_id,
            title: r.title,
            due_date: r.due_date ?? "",
            assigned_at: r.assigned_at ?? "",
            status: (local.find((x) => x.id === r.id)?.status ?? r.status ?? "pending") as AssignmentItem["status"],
          };
          merged.push(a);
          if (!localIds.has(r.id)) {
            localIds.add(r.id);
            push({
              type: "assignment",
              title: "📋 New Quiz Assigned",
              message: `${a.title} — due ${a.due_date || "TBD"}`,
              pinned: true,
              action: {
                label: "Start Quiz",
                href: `/quiz/${a.quiz_id}`,
              },
            });
          }
        }

        if (merged.length > 0) {
          saveAssignmentsToStorage(merged);
        }
      } catch {
        /* offline or not configured */
      }
    };

    run();
  }, [profile.profile_mode, profile.class_code, connectivityStatus, push]);

  return null;
}
