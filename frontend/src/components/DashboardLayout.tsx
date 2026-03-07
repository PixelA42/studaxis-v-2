/**
 * Dashboard layout — sidebar + main content. Used for all app routes that need nav.
 */

import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";

export function DashboardLayout() {
  return (
    <div className="min-h-screen flex">
      <div className="ambient-glow" aria-hidden />
      <Sidebar />
      <main className="flex-1 relative z-10 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
