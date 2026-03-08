/**
 * Dashboard layout — sidebar + main content. Used for all app routes that need nav.
 * Hides sidebar when Panic Mode is active (fullscreen exam) or when on /panic-mode route.
 */

import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { useRecentToolsTracker } from "../hooks/useRecentTools";
import { usePanicExam } from "../contexts/PanicExamContext";
import { useAuth } from "../contexts/AuthContext";

export function DashboardLayout() {
  useRecentToolsTracker();
  const { examActive } = usePanicExam();
  const { connectivityStatus } = useAuth();
  const location = useLocation();
  const inPanicMode = location.pathname.includes("/panic-mode");

  const hideSidebar = examActive || inPanicMode;

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
      {!hideSidebar && <Sidebar />}
      <main className={`flex-1 min-w-0 relative z-10 flex flex-col min-h-0 overflow-hidden p-6 ${hideSidebar ? "" : ""}`}>
        {connectivityStatus === "offline" && (
          <div
            className="flex-shrink-0 py-2 px-4 text-center text-sm text-primary/90 bg-amber-500/15 border-b border-amber-500/30"
            role="status"
          >
            Offline. Data will sync when online.
          </div>
        )}
        <div className="flex-1 min-h-0 overflow-x-hidden overflow-y-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
