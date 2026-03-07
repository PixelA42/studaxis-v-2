/**
 * Dashboard layout — sidebar + main content. Used for all app routes that need nav.
 * Hides sidebar when Panic Mode exam is active (navbar locked during test).
 */

import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { useRecentToolsTracker } from "../hooks/useRecentTools";
import { usePanicExam } from "../contexts/PanicExamContext";

export function DashboardLayout() {
  useRecentToolsTracker();
  const { examActive } = usePanicExam();

  return (
    <div className="min-h-screen flex bg-deep">
      <div className="ambient-glow" aria-hidden />
      {!examActive && <Sidebar />}
      <main className={`flex-1 relative z-10 overflow-auto p-6 ${examActive ? "" : ""}`}>
        <Outlet />
      </main>
    </div>
  );
}
