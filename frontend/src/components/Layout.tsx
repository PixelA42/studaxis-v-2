/**
 * Layout — main app shell with glassmorphic sidebar (Thermal Vitreous).
 * Navigation: Dashboard, Chat, Flashcards.
 * Renders child routes via <Outlet />.
 */

import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/chat", label: "Chat", end: false },
  { to: "/flashcards", label: "Flashcards", end: false },
] as const;

export function Layout() {
  return (
    <div className="min-h-screen bg-deep text-primary flex">
      {/* Ambient glow (background) */}
      <div className="ambient-glow" aria-hidden />

      {/* Sidebar — glassmorphic */}
      <aside
        className="w-56 min-h-screen flex-shrink-0 glass-panel rounded-r-2xl border-l-0 border-t-0 border-b-0 flex flex-col z-10"
        aria-label="Main navigation"
      >
        <div className="p-5 border-b border-glass-border">
          <h1 className="font-sans font-semibold text-lg tracking-tight text-primary">
            Studaxis
          </h1>
          <p className="text-xs text-primary/70 mt-0.5">Offline-first tutor</p>
        </div>
        <nav className="flex-1 p-3 flex flex-col gap-1">
          {navItems.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }: { isActive: boolean }) =>
                `px-4 py-3 rounded-xl font-medium text-sm transition-colors ${
                  isActive
                    ? "bg-accent-blue/20 text-accent-blue border border-glass-border"
                    : "text-primary/80 hover:bg-surface-light hover:text-primary border border-transparent"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-glass-border">
          <p className="text-xs text-primary/50">Thermal Vitreous</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 relative z-10 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
