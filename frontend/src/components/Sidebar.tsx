/**
 * Sidebar — collapsible nav (Thermal Vitreous). Matches Streamlit nav: Core, Analytics, System, Footer.
 * Toggle state in localStorage.
 */

import { type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { StatusIndicator } from "./StatusIndicator";
import { useCallback, useEffect, useState } from "react";
import { Icons } from "./icons";

const STORAGE_SIDEBAR = "studaxis_sidebar_state";

const navSections: {
  label: string;
  items: { to: string; label: string; icon: ReactNode; badge?: number; panic?: boolean }[];
}[] = [
  {
    label: "Core Tools",
    items: [
      { to: "/home", label: "Home", icon: Icons.home },
      { to: "/dashboard", label: "Dashboard", icon: Icons.dashboard },
      { to: "/chat", label: "AI Chat", icon: Icons.ai },
      { to: "/flashcards", label: "Flashcards", icon: Icons.cards },
      { to: "/quiz", label: "Quiz", icon: Icons.quiz },
    ],
  },
  {
    label: "Analytics",
    items: [
      { to: "/insights", label: "Insights", icon: Icons.insights },
      { to: "/panic-mode", label: "Panic Mode", icon: Icons.panic, panic: true },
    ],
  },
  {
    label: "System",
    items: [
      { to: "/conflicts", label: "Conflicts", icon: Icons.conflicts, badge: 0 },
      { to: "/sync", label: "Sync Status", icon: Icons.sync },
    ],
  },
  {
    label: "",
    items: [
      { to: "/settings", label: "Settings", icon: Icons.settings },
      { to: "/profile", label: "Profile", icon: Icons.profile },
    ],
  },
];

function getStoredCollapsed(): boolean {
  return localStorage.getItem(STORAGE_SIDEBAR) === "collapsed";
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(getStoredCollapsed);
  const { profile, connectivityStatus } = useAuth();

  const toggle = useCallback(() => {
    setCollapsed((c) => {
      const next = !c;
      localStorage.setItem(STORAGE_SIDEBAR, next ? "collapsed" : "expanded");
      return next;
    });
  }, []);

  useEffect(() => {
    setCollapsed(getStoredCollapsed());
  }, []);

  const profileName = profile.profile_name || "Student";

  return (
    <aside
      className={`relative flex flex-col flex-shrink-0 content-card border-r border-t-0 border-b-0 border-l-0 rounded-r-2xl transition-all duration-300 z-10 ${
        collapsed ? "w-sidebar-collapsed" : "w-sidebar"
      }`}
      aria-label="Main navigation"
    >
      <button
        type="button"
        onClick={toggle}
        className="absolute -right-3 top-1/2 -translate-y-1/2 z-20 w-7 h-7 rounded-full bg-white border border-heading-dark/10 flex items-center justify-center text-heading-dark/80 hover:text-accent-blue hover:border-accent-blue shadow-card transition-colors"
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        <span className={`text-xs transition-transform ${collapsed ? "rotate-180" : ""}`}>‹</span>
      </button>

      <div className={`p-5 border-b border-glass-border ${collapsed ? "flex justify-center" : ""}`}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-blue flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
            S
          </div>
          {!collapsed && (
            <span className="font-bold text-heading-dark truncate">Studaxis</span>
          )}
        </div>
      </div>

      <nav className="flex-1 overflow-hidden flex flex-col py-3">
        {navSections.map((section) => (
          <div key={section.label || "footer"} className="mb-4">
            {section.label && !collapsed && (
              <div className="px-4 py-1.5 text-[10px] font-mono uppercase tracking-wider text-heading-dark/60">
                {section.label}
              </div>
            )}
            <div className="flex flex-col gap-0.5">
              {section.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/home" || item.to === "/dashboard"}
                    className={({ isActive: active }) =>
                      `flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                        collapsed ? "justify-center" : ""
                      } ${
                        active
                          ? "bg-accent-blue text-white border-l-0"
                          : item.panic
                            ? "text-heading-dark/80 hover:bg-chunk-pink/20 hover:text-chunk-pink"
                            : "text-heading-dark/80 hover:bg-heading-dark/5 hover:text-heading-dark"
                      }`
                    }
                  >
                    <span className="flex-shrink-0 w-6 flex items-center justify-center" aria-hidden>
                      {item.icon}
                    </span>
                    {!collapsed && (
                      <>
                        <span className="truncate">{item.label}</span>
                        {item.badge != null && item.badge > 0 && (
                          <span className="ml-auto text-[10px] bg-error/20 text-error px-1.5 py-0.5 rounded-full">
                            {item.badge}
                          </span>
                        )}
                      </>
                    )}
                  </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className={`p-3 border-t border-glass-border ${collapsed ? "flex justify-center" : ""}`}>
        {!collapsed && (
          <>
            <p className="text-xs text-heading-dark/60 truncate font-medium">{profileName}</p>
            <div className="mt-2">
              <StatusIndicator status={connectivityStatus} />
            </div>
          </>
        )}
      </div>
    </aside>
  );
}
