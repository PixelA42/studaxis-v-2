/**
 * NotificationContext — Foundation for quiz assignments, sync alerts, streak reminders.
 * State persisted to localStorage; backend merge on load (backend wins for assignments).
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { getNotifications as apiGetNotifications } from "../services/api";
import { NotificationTray } from "../components/NotificationTray";

const STORAGE_KEY = "studaxis_notifications";

export type NotificationType =
  | "info"
  | "success"
  | "warning"
  | "error"
  | "sync"
  | "update"
  | "assignment"
  | "streak";

export interface NotificationAction {
  label: string;
  href: string;
}

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
  tag?: string;
  pinned?: boolean;
  read: boolean;
  timestamp: string;
  action?: NotificationAction;
}

export interface NotificationPushInput {
  type?: NotificationType;
  title: string;
  message?: string;
  tag?: string;
  pinned?: boolean;
  action?: NotificationAction;
}

const ACCENT_COLORS: Record<NotificationType, string> = {
  info: "#00a8e8",
  success: "#10b981",
  warning: "#FEC288",
  error: "#FA5C5C",
  sync: "#8b5cf6",
  update: "#FBEF76",
  assignment: "#FD8A6B",
  streak: "#FD8A6B",
};

let _id = 1;
function mkId() {
  return `notif_${_id++}_${Date.now()}`;
}

function loadFromStorage(): Notification[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.map((n: Record<string, unknown>) => ({
      id: String(n.id ?? mkId()),
      type: (n.type as NotificationType) ?? "info",
      title: String(n.title ?? ""),
      message: n.message != null ? String(n.message) : undefined,
      tag: n.tag != null ? String(n.tag) : undefined,
      pinned: Boolean(n.pinned),
      read: Boolean(n.read),
      timestamp: String(n.timestamp ?? ""),
      action:
        n.action && typeof n.action === "object"
          ? {
              label: String((n.action as { label?: unknown }).label ?? ""),
              href: String((n.action as { href?: unknown }).href ?? ""),
            }
          : undefined,
    }));
  } catch {
    return [];
  }
}

function saveToStorage(notifications: Notification[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications));
  } catch {
    // ignore
  }
}

/* ═══════════════════════════════════════════════
   TOAST (max 3, 4s auto-dismiss, pinned stay)
═══════════════════════════════════════════════ */
const TOAST_DURATION_MS = 4000;
const MAX_TOASTS = 3;

interface ToastItem {
  id: string;
  notif: Notification;
  timer: ReturnType<typeof setTimeout> | null;
}

interface NotificationContextValue {
  notifications: Notification[];
  unreadCount: number;
  push: (input: NotificationPushInput) => string;
  dismiss: (id: string) => void;
  markRead: (id: string) => void;
  markAllRead: () => void;
  pin: (id: string) => void;
  clearAll: () => void;
  trayOpen: boolean;
  openTray: () => void;
  closeTray: () => void;
  getAccentColor: (type: NotificationType) => string;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>(() =>
    loadFromStorage()
  );
  const [trayOpen, setTrayOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const toastsRef = useRef<ToastItem[]>([]);

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.read).length,
    [notifications]
  );

  const persist = useCallback((next: Notification[]) => {
    setNotifications(next);
    saveToStorage(next);
  }, []);

  const push = useCallback(
    (input: NotificationPushInput): string => {
      const id = mkId();
      const timestamp = new Date().toISOString();
      const notif: Notification = {
        id,
        type: (input.type ?? "info") as NotificationType,
        title: input.title,
        message: input.message,
        tag: input.tag,
        pinned: input.pinned ?? false,
        read: false,
        timestamp,
        action: input.action,
      };
      persist([notif, ...notifications]);

      // Toast: show up to MAX_TOASTS; pinned stay until manually closed
      const toastItem: ToastItem = {
        id: notif.id,
        notif,
        timer: null,
      };
      if (!notif.pinned) {
        toastItem.timer = setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== id));
        }, TOAST_DURATION_MS);
      }
      setToasts((prev) => {
        const next = [toastItem, ...prev.filter((t) => t.id !== id)].slice(
          0,
          MAX_TOASTS
        );
        toastsRef.current = next;
        return next;
      });

      return id;
    },
    [notifications, persist]
  );

  const dismiss = useCallback(
    (id: string) => {
      setToasts((prev) => {
        const t = prev.find((x) => x.id === id);
        if (t?.timer) clearTimeout(t.timer);
        return prev.filter((x) => x.id !== id);
      });
      persist(notifications.filter((n) => n.id !== id));
    },
    [notifications, persist]
  );

  const markRead = useCallback(
    (id: string) => {
      const n = notifications.find((x) => x.id === id);
      if (!n || n.read) return;
      persist(
        notifications.map((x) =>
          x.id === id ? { ...x, read: true } : x
        )
      );
    },
    [notifications, persist]
  );

  const markAllRead = useCallback(() => {
    const hasUnread = notifications.some((n) => !n.read);
    if (!hasUnread) return;
    persist(
      notifications.map((n) => (n.read ? n : { ...n, read: true }))
    );
  }, [notifications, persist]);

  const pin = useCallback(
    (id: string) => {
      persist(
        notifications.map((n) =>
          n.id === id ? { ...n, pinned: !n.pinned } : n
        )
      );
    },
    [notifications, persist]
  );

  const clearAll = useCallback(() => {
    const toKeep = notifications.filter((n) => n.pinned);
    if (toKeep.length === notifications.length) return;
    persist(toKeep);
  }, [notifications, persist]);

  const openTray = useCallback(() => {
    setTrayOpen(true);
    markAllRead();
  }, [markAllRead]);

  const closeTray = useCallback(() => setTrayOpen(false), []);

  const getAccentColor = useCallback((type: NotificationType) => {
    return ACCENT_COLORS[type] ?? ACCENT_COLORS.info;
  }, []);

  // Fetch from backend on load, merge (backend wins for assignment)
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        const backend = await apiGetNotifications();
        if (cancelled || !backend?.length) return;
        setNotifications((local) => {
          const byId = new Map<string, Notification>();
          for (const n of local) {
            byId.set(n.id, n);
          }
          for (const b of backend) {
            const n: Notification = {
              id: String(b.id),
              type: (b.type as NotificationType) ?? "info",
              title: String(b.title ?? ""),
              message: b.message != null ? String(b.message) : undefined,
              tag: b.tag != null ? String(b.tag) : undefined,
              pinned: Boolean(b.pinned),
              read: Boolean(b.read),
              timestamp: String(b.timestamp ?? ""),
              action:
                b.action && typeof b.action === "object"
                  ? {
                      label: String(b.action.label ?? ""),
                      href: String(b.action.href ?? ""),
                    }
                  : undefined,
            };
            const existing = byId.get(n.id);
            if (n.type === "assignment" || !existing) {
              byId.set(n.id, n);
            }
          }
          const merged = Array.from(byId.values()).sort(
            (a, b) =>
              new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
          );
          saveToStorage(merged);
          return merged;
        });
      } catch {
        // Offline or not logged in: keep localStorage only
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    saveToStorage(notifications);
  }, [notifications]);

  const value = useMemo<NotificationContextValue>(
    () => ({
      notifications,
      unreadCount,
      push,
      dismiss,
      markRead,
      markAllRead,
      pin,
      clearAll,
      trayOpen,
      openTray,
      closeTray,
      getAccentColor,
    }),
    [
      notifications,
      unreadCount,
      push,
      dismiss,
      markRead,
      markAllRead,
      pin,
      clearAll,
      trayOpen,
      openTray,
      closeTray,
      getAccentColor,
    ]
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <ToastStack
        toasts={toasts}
        onDismiss={dismiss}
        getAccentColor={getAccentColor}
        onOpenTray={openTray}
      />
      {trayOpen && <NotificationTray />}
      <style>{`
        @keyframes slideInRight {
          from { opacity: 0; transform: translateX(24px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes slideIn {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes notificationTraySlideIn {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
      `}</style>
    </NotificationContext.Provider>
  );
}

function ToastStack({
  toasts,
  onDismiss,
  getAccentColor,
  onOpenTray,
}: {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
  getAccentColor: (t: NotificationType) => string;
  onOpenTray: () => void;
}) {
  if (toasts.length === 0) return null;
  return (
    <div
      style={{
        position: "fixed",
        top: 20,
        right: 20,
        zIndex: 300,
        display: "flex",
        flexDirection: "column",
        gap: 10,
        alignItems: "flex-end",
        pointerEvents: "all",
      }}
    >
      {toasts.map((t) => (
        <ToastCard
          key={t.notif.id}
          notif={t.notif}
          accentColor={getAccentColor(t.notif.type)}
          onDismiss={() => onDismiss(t.notif.id)}
          onOpenTray={onOpenTray}
        />
      ))}
    </div>
  );
}

function ToastCard({
  notif,
  accentColor,
  onDismiss,
  onOpenTray,
}: {
  notif: Notification;
  accentColor: string;
  onDismiss: () => void;
  onOpenTray: () => void;
}) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 10);
    return () => clearTimeout(t);
  }, []);

  const firstLine = notif.message?.split("\n")[0] ?? "";
  const messageLine = firstLine ? (firstLine.length > 80 ? firstLine.slice(0, 80) + "…" : firstLine) : null;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onOpenTray()}
      onKeyDown={(e) => e.key === "Enter" && onOpenTray()}
      style={{
        width: 320,
        maxWidth: "calc(100vw - 40px)",
        background: "var(--surface-light)",
        borderLeft: `4px solid ${accentColor}`,
        border: "1.5px solid var(--glass-border)",
        borderRadius: 14,
        boxShadow: "var(--card-shadow)",
        overflow: "hidden",
        transform: visible ? "translateX(0)" : "translateY(-20px)",
        opacity: visible ? 1 : 0,
        transition: "transform .3s ease, opacity .3s ease",
        cursor: "pointer",
      }}
    >
      <div style={{ padding: "14px 16px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 8,
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: "var(--text-primary)",
              }}
            >
              {notif.title}
            </div>
            {messageLine && (
              <div
                style={{
                  fontSize: 12,
                  color: "var(--text-muted)",
                  marginTop: 4,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {messageLine}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDismiss();
            }}
            style={{
              width: 24,
              height: 24,
              border: "none",
              background: "transparent",
              color: "var(--text-subtle)",
              cursor: "pointer",
              padding: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 6,
            }}
            aria-label="Dismiss"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

export function useNotification(): NotificationContextValue {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error("useNotification must be used within NotificationProvider");
  }
  return ctx;
}
