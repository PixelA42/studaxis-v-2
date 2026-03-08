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
    <div
      className="flex h-screen overflow-hidden bg-deep"
      style={{
        display: "flex",
        flexDirection: "row",
        height: "100%",
        width: "100%",
        overflow: "hidden",
      }}
    >
      <div className="ambient-glow" aria-hidden />
      {!examActive && <Sidebar />}
      <main className={`flex-1 min-w-0 relative z-10 flex flex-col min-h-0 overflow-hidden p-6 ${examActive ? "" : ""}`}>
        <div className="flex-1 min-h-0 overflow-x-hidden overflow-y-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
