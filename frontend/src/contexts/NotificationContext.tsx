/**
 * NotificationContext — Global notification system for Studaxis.
 * Manages toast tray, history drawer, position preference, and localStorage persistence.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  useRef,
  type ReactNode,
} from "react";

/* ═══════════════════════════════════════════════
   NOTIFICATION CONFIG
═══════════════════════════════════════════════ */
const TYPES: Record<
  string,
  { bg: string; border: string; icon_bg: string; text: string; label: string }
> = {
  info: {
    bg: "#e8f7ff",
    border: "#00a8e8",
    icon_bg: "#00a8e8",
    text: "#005f8a",
    label: "Info",
  },
  success: {
    bg: "#f0fdf6",
    border: "#10b981",
    icon_bg: "#10b981",
    text: "#065f46",
    label: "Success",
  },
  warning: {
    bg: "#fffbeb",
    border: "#FEC288",
    icon_bg: "#FD8A6B",
    text: "#7c4a00",
    label: "Warning",
  },
  error: {
    bg: "#fff5f5",
    border: "#FA5C5C",
    icon_bg: "#FA5C5C",
    text: "#7f1d1d",
    label: "Error",
  },
  sync: {
    bg: "#f5f0ff",
    border: "#8b5cf6",
    icon_bg: "#8b5cf6",
    text: "#4c1d95",
    label: "Sync",
  },
  update: {
    bg: "#fffaf0",
    border: "#FBEF76",
    icon_bg: "#FEC288",
    text: "#78530a",
    label: "Update",
  },
};

export const POSITIONS = [
  "top-right",
  "top-left",
  "top-center",
  "bottom-right",
  "bottom-left",
  "bottom-center",
] as const;

export type NotificationPosition = (typeof POSITIONS)[number];

let _id = 1;
const mkId = () => `notif_${_id++}`;

/* ═══════════════════════════════════════════════
   ICONS
═══════════════════════════════════════════════ */
const Icons: Record<
  string,
  ((c: string) => JSX.Element) | JSX.Element
> = {
  info: (c) => (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke={c} strokeWidth="2" />
      <path
        d="M12 16v-4M12 8h.01"
        stroke={c}
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  ),
  success: (c) => (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke={c} strokeWidth="2" />
      <path
        d="M9 12l2 2 4-4"
        stroke={c}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
  warning: (c) => (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
      <path
        d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
        stroke={c}
        strokeWidth="2"
      />
      <path
        d="M12 9v4M12 17h.01"
        stroke={c}
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  ),
  error: (c) => (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke={c} strokeWidth="2" />
      <path
        d="M15 9l-6 6M9 9l6 6"
        stroke={c}
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  ),
  sync: (c) => (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
      <path
        d="M4 4v5h5M20 20v-5h-5M4.07 15a9 9 0 100-5.88"
        stroke={c}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
  update: (c) => (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
      <path
        d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"
        stroke={c}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
  close: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path
        d="M18 6L6 18M6 6l12 12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  ),
  edit: (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
      <path
        d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  ),
  pin: (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ),
};

/* ═══════════════════════════════════════════════
   TYPES
═══════════════════════════════════════════════ */
export interface NotificationAction {
  label: string;
  onClick: () => void;
}

export interface NotificationConfig {
  type?: string;
  title: string;
  message?: string;
  duration?: number;
  tag?: string;
  pinned?: boolean;
  action?: NotificationAction;
}

export interface Notification extends NotificationConfig {
  id: string;
  timestamp: string;
}

/* ═══════════════════════════════════════════════
   LOCAL STORAGE
═══════════════════════════════════════════════ */
const STORAGE_HISTORY = "studaxis_notification_history";
const STORAGE_POSITION = "studaxis_notification_position";
const MAX_HISTORY = 100;

function loadHistory(): Notification[] {
  try {
    const raw = localStorage.getItem(STORAGE_HISTORY);
    if (raw) {
      const arr = JSON.parse(raw) as Array<Record<string, unknown>>;
      return arr.slice(0, MAX_HISTORY).map((item) => ({
        ...item,
        id: String(item.id ?? mkId()),
        timestamp: String(item.timestamp ?? ""),
      })) as Notification[];
    }
  } catch {
    // ignore
  }
  return [];
}

function saveHistory(history: Notification[]) {
  try {
    const sanitized = history.slice(-MAX_HISTORY).map(({ id, type, title, message, duration, tag, pinned, timestamp }) => ({
      id,
      type,
      title,
      message,
      duration,
      tag,
      pinned,
      timestamp,
    }));
    localStorage.setItem(STORAGE_HISTORY, JSON.stringify(sanitized));
  } catch {
    // ignore
  }
}

function loadPosition(): NotificationPosition {
  try {
    const raw = localStorage.getItem(STORAGE_POSITION);
    if (raw && POSITIONS.includes(raw as NotificationPosition)) {
      return raw as NotificationPosition;
    }
  } catch {
    // ignore
  }
  return "top-right";
}

function savePosition(position: NotificationPosition) {
  try {
    localStorage.setItem(STORAGE_POSITION, position);
  } catch {
    // ignore
  }
}

/* ═══════════════════════════════════════════════
   SINGLE NOTIFICATION CARD
═══════════════════════════════════════════════ */
const iconBtn = {
  width: "24px",
  height: "24px",
  borderRadius: "6px",
  border: "none",
  background: "transparent",
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  transition: "color .15s, background .15s",
  padding: 0,
} as const;

function NotifCard({
  notif,
  onDismiss,
  onEdit,
  onPin,
}: {
  notif: Notification;
  onDismiss: (id: string) => void;
  onEdit: (n: Notification) => void;
  onPin: (id: string) => void;
}) {
  const [visible, setVisible] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [progress, setProgress] = useState(100);
  const [paused, setPaused] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const cfg = TYPES[notif.type ?? "info"] ?? TYPES.info;

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 10);
    return () => clearTimeout(t);
  }, []);

  const dismiss = useCallback(() => {
    setLeaving(true);
    setTimeout(() => onDismiss(notif.id), 320);
  }, [notif.id, onDismiss]);

  useEffect(() => {
    if (!notif.duration || notif.pinned) return;
    if (paused) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }
    const step = 100 / (notif.duration / 50);
    intervalRef.current = setInterval(() => {
      setProgress((p) => {
        if (p <= 0) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          dismiss();
          return 0;
        }
        return p - step;
      });
    }, 50);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [paused, notif.duration, notif.pinned, dismiss]);

  const IconComp = Icons[notif.type ?? "info"] ?? Icons.info;
  const iconEl =
    typeof IconComp === "function" ? IconComp(cfg.icon_bg) : IconComp;

  return (
    <div
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      style={{
        width: "340px",
        maxWidth: "calc(100vw - 32px)",
        background: notif.pinned ? "#fff" : cfg.bg,
        border: `1.5px solid ${cfg.border}`,
        borderRadius: "14px",
        boxShadow: `0 4px 20px ${cfg.border}20, 0 1px 6px rgba(0,0,0,0.06)`,
        overflow: "hidden",
        transform: leaving
          ? "translateX(110%)"
          : visible
            ? "translateX(0) scale(1)"
            : "translateX(110%) scale(0.95)",
        opacity: leaving ? 0 : visible ? 1 : 0,
        transition:
          "transform .32s cubic-bezier(0.16,1,0.3,1), opacity .32s ease",
        marginBottom: "10px",
        position: "relative",
      }}
    >
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: "4px",
          background: `linear-gradient(180deg,${cfg.icon_bg},${cfg.border}aa)`,
          borderRadius: "14px 0 0 14px",
        }}
      />

      <div
        style={{
          padding: "13px 14px 13px 18px",
          display: "flex",
          alignItems: "flex-start",
          gap: "10px",
        }}
      >
        <div
          style={{
            width: "30px",
            height: "30px",
            borderRadius: "8px",
            background: `${cfg.icon_bg}18`,
            border: `1px solid ${cfg.icon_bg}30`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            marginTop: "1px",
          }}
        >
          {iconEl}
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              marginBottom: "3px",
            }}
          >
            <span
              style={{
                fontSize: "11px",
                fontWeight: 700,
                color: cfg.icon_bg,
                letterSpacing: "0.3px",
                textTransform: "uppercase",
              }}
            >
              {cfg.label}
            </span>
            {notif.pinned && (
              <span
                style={{
                  fontSize: "9.5px",
                  fontWeight: 700,
                  background: `${cfg.icon_bg}18`,
                  color: cfg.icon_bg,
                  border: `1px solid ${cfg.icon_bg}30`,
                  borderRadius: "20px",
                  padding: "1px 6px",
                }}
              >
                PINNED
              </span>
            )}
            {notif.tag && (
              <span
                style={{
                  fontSize: "9.5px",
                  fontWeight: 600,
                  background: "rgba(0,0,0,0.06)",
                  color: "#6b7280",
                  borderRadius: "20px",
                  padding: "1px 6px",
                }}
              >
                {notif.tag}
              </span>
            )}
          </div>
          <div
            style={{
              fontSize: "13.5px",
              fontWeight: 700,
              color: "#0d1b2a",
              lineHeight: 1.3,
              marginBottom: "3px",
            }}
          >
            {notif.title}
          </div>
          {notif.message && (
            <div style={{ fontSize: "12px", color: "#6b7280", lineHeight: 1.5 }}>
              {notif.message}
            </div>
          )}
          {notif.action && (
            <button
              onClick={notif.action.onClick}
              style={{
                marginTop: "8px",
                padding: "5px 12px",
                borderRadius: "7px",
                border: "none",
                background: `linear-gradient(135deg,${cfg.icon_bg},${cfg.border})`,
                color: "#fff",
                fontSize: "11.5px",
                fontWeight: 700,
                cursor: "pointer",
                fontFamily: "inherit",
                boxShadow: `0 2px 8px ${cfg.icon_bg}35`,
              }}
            >
              {notif.action.label}
            </button>
          )}
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "5px",
            flexShrink: 0,
          }}
        >
          <button
            onClick={dismiss}
            style={{ ...iconBtn, color: "#9ca3af" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#FA5C5C")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#9ca3af")}
          >
            {Icons.close as JSX.Element}
          </button>
          <button
            onClick={() => onPin(notif.id)}
            style={{
              ...iconBtn,
              color: notif.pinned ? "#FD8A6B" : "#9ca3af",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#FD8A6B")}
            onMouseLeave={(e) =>
              (e.currentTarget.style.color = notif.pinned ? "#FD8A6B" : "#9ca3af")
            }
            title={notif.pinned ? "Unpin" : "Pin"}
          >
            {Icons.pin as JSX.Element}
          </button>
          <button
            onClick={() => onEdit(notif)}
            style={{ ...iconBtn, color: "#9ca3af" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#00a8e8")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#9ca3af")}
            title="Edit"
          >
            {Icons.edit as JSX.Element}
          </button>
        </div>
      </div>

      {notif.duration && !notif.pinned && (
        <div style={{ height: "3px", background: "rgba(0,0,0,0.06)" }}>
          <div
            style={{
              height: "100%",
              width: `${progress}%`,
              background: `linear-gradient(90deg,${cfg.icon_bg},${cfg.border})`,
              transition: paused ? "none" : "width .05s linear",
              borderRadius: "0 3px 3px 0",
            }}
          />
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════
   NOTIFICATION TRAY
═══════════════════════════════════════════════ */
function NotifTray({
  notifs,
  position,
  onDismiss,
  onEdit,
  onPin,
}: {
  notifs: Notification[];
  position: NotificationPosition;
  onDismiss: (id: string) => void;
  onEdit: (n: Notification) => void;
  onPin: (id: string) => void;
}) {
  const isBottom = position.startsWith("bottom");
  const isCenter = position.endsWith("center");
  const isLeft = position.endsWith("left");

  const posStyle: React.CSSProperties = {
    position: "fixed",
    zIndex: 9999,
    [isBottom ? "bottom" : "top"]: "20px",
    ...(isCenter
      ? { left: "50%", transform: "translateX(-50%)" }
      : isLeft
        ? { left: "20px" }
        : { right: "20px" }),
    display: "flex",
    flexDirection: isBottom ? "column-reverse" : "column",
    alignItems: isCenter ? "center" : isLeft ? "flex-start" : "flex-end",
    pointerEvents: "none",
  };

  return (
    <div style={posStyle}>
      {notifs.map((n) => (
        <div key={n.id} style={{ pointerEvents: "all" }}>
          <NotifCard
            notif={n}
            onDismiss={onDismiss}
            onEdit={onEdit}
            onPin={onPin}
          />
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════
   EDIT MODAL
═══════════════════════════════════════════════ */
const lbl = {
  display: "block",
  fontSize: "12px",
  fontWeight: 700,
  color: "#374151",
  marginBottom: "6px",
} as const;

function EditModal({
  notif,
  onSave,
  onClose,
}: {
  notif: Notification;
  onSave: (n: Notification) => void;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(notif.title);
  const [message, setMessage] = useState(notif.message ?? "");
  const [type, setType] = useState(notif.type ?? "info");

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(13,27,42,0.5)",
        zIndex: 10000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backdropFilter: "blur(4px)",
        animation: "fadeIn .2s ease",
      }}
    >
      <div
        style={{
          width: "420px",
          maxWidth: "calc(100vw-32px)",
          background: "#fff",
          borderRadius: "20px",
          padding: "28px",
          boxShadow: "0 20px 60px rgba(0,0,0,0.2)",
          animation: "popIn .3s cubic-bezier(0.16,1,0.3,1)",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: "4px",
            borderRadius: "20px 20px 0 0",
            background:
              "linear-gradient(90deg,#FA5C5C,#FD8A6B,#FEC288)",
          }}
        />
        <h3
          style={{
            fontSize: "16px",
            fontWeight: 900,
            color: "#0d1b2a",
            marginBottom: "18px",
            letterSpacing: "-0.3px",
          }}
        >
          Edit Notification
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div>
            <label style={lbl}>Type</label>
            <div style={{ display: "flex", gap: "7px", flexWrap: "wrap" }}>
              {Object.entries(TYPES).map(([k, v]) => (
                <button
                  key={k}
                  onClick={() => setType(k)}
                  style={{
                    padding: "5px 12px",
                    borderRadius: "20px",
                    border: `1.5px solid ${type === k ? v.icon_bg : "#e5e7eb"}`,
                    background: type === k ? `${v.icon_bg}12` : "#fafbfc",
                    fontSize: "11.5px",
                    fontWeight: 700,
                    color: type === k ? v.icon_bg : "#6b7280",
                    cursor: "pointer",
                    fontFamily: "inherit",
                    transition: "all .15s",
                  }}
                >
                  {v.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label style={lbl}>Title</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 12px",
                border: "1.5px solid #e8edf5",
                borderRadius: "10px",
                fontSize: "13.5px",
                color: "#0d1b2a",
                fontFamily: "inherit",
                outline: "none",
                background: "#fafbfc",
              }}
              onFocus={(e) => (e.target.style.borderColor = "#FA5C5C")}
              onBlur={(e) => (e.target.style.borderColor = "#e8edf5")}
            />
          </div>
          <div>
            <label style={lbl}>Message</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              style={{
                width: "100%",
                padding: "10px 12px",
                border: "1.5px solid #e8edf5",
                borderRadius: "10px",
                fontSize: "13px",
                color: "#0d1b2a",
                fontFamily: "inherit",
                outline: "none",
                background: "#fafbfc",
                resize: "vertical",
              }}
              onFocus={(e) => (e.target.style.borderColor = "#FA5C5C")}
              onBlur={(e) => (e.target.style.borderColor = "#e8edf5")}
            />
          </div>
        </div>
        <div style={{ display: "flex", gap: "10px", marginTop: "20px" }}>
          <button
            onClick={() =>
              onSave({ ...notif, title, message, type } as Notification)
            }
            style={{
              flex: 1,
              height: "44px",
              borderRadius: "11px",
              border: "none",
              background: "linear-gradient(135deg,#FA5C5C,#FD8A6B)",
              color: "#fff",
              fontSize: "14px",
              fontWeight: 700,
              cursor: "pointer",
              fontFamily: "inherit",
              boxShadow: "0 3px 12px rgba(250,92,92,0.35)",
            }}
          >
            Save Changes
          </button>
          <button
            onClick={onClose}
            style={{
              padding: "0 20px",
              height: "44px",
              borderRadius: "11px",
              border: "1.5px solid #e8edf5",
              background: "#fafbfc",
              fontSize: "14px",
              fontWeight: 600,
              color: "#6b7280",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════
   HISTORY DRAWER
═══════════════════════════════════════════════ */
function HistoryDrawer({
  all,
  onClear,
  onReplay,
  onClose,
}: {
  all: Notification[];
  onClear: () => void;
  onReplay: (n: NotificationConfig) => void;
  onClose: () => void;
}) {
  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        bottom: 0,
        width: "340px",
        background: "#fff",
        borderLeft: "1.5px solid #e8edf5",
        boxShadow: "-8px 0 32px rgba(0,0,0,0.1)",
        zIndex: 9998,
        display: "flex",
        flexDirection: "column",
        animation: "slideInRight .3s cubic-bezier(0.16,1,0.3,1)",
      }}
    >
      <div
        style={{
          padding: "20px 18px 14px",
          borderBottom: "1px solid #f1f3f8",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <div
            style={{
              fontSize: "15px",
              fontWeight: 900,
              color: "#0d1b2a",
              letterSpacing: "-0.3px",
            }}
          >
            Notification Log
          </div>
          <div style={{ fontSize: "11px", color: "#9ca3af", marginTop: "2px" }}>
            {all.length} total events
          </div>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={onClear}
            style={{
              padding: "6px 12px",
              borderRadius: "8px",
              border: "1.5px solid #e8edf5",
              background: "#fafbfc",
              fontSize: "11.5px",
              fontWeight: 700,
              color: "#6b7280",
              cursor: "pointer",
              fontFamily: "inherit",
              transition: "all .15s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "#FA5C5C";
              e.currentTarget.style.color = "#FA5C5C";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "#e8edf5";
              e.currentTarget.style.color = "#6b7280";
            }}
          >
            Clear All
          </button>
          <button
            onClick={onClose}
            style={{
              ...iconBtn,
              color: "#9ca3af",
              border: "1.5px solid #e8edf5",
              borderRadius: "8px",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#FA5C5C")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#9ca3af")}
          >
            {Icons.close as JSX.Element}
          </button>
        </div>
      </div>

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px 14px",
        }}
      >
        {all.length === 0 && (
          <div
            style={{
              textAlign: "center",
              padding: "40px 0",
              color: "#9ca3af",
              fontSize: "13px",
            }}
          >
            No notifications yet
          </div>
        )}
        {[...all].reverse().map((n, i) => {
          const cfg = TYPES[n.type ?? "info"] ?? TYPES.info;
          const IconComp = Icons[n.type ?? "info"] ?? Icons.info;
          const iconEl =
            typeof IconComp === "function" ? IconComp(cfg.icon_bg) : IconComp;
          return (
            <div
              key={`${n.id}-${i}`}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "10px 12px",
                borderRadius: "11px",
                marginBottom: "6px",
                background: cfg.bg,
                border: `1px solid ${cfg.border}25`,
                transition: "all .15s",
              }}
            >
              <div
                style={{
                  width: "26px",
                  height: "26px",
                  borderRadius: "7px",
                  background: `${cfg.icon_bg}18`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                {iconEl}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: "12.5px",
                    fontWeight: 700,
                    color: "#0d1b2a",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {n.title}
                </div>
                <div
                  style={{
                    fontSize: "10.5px",
                    color: "#9ca3af",
                    marginTop: "1px",
                  }}
                >
                  {n.timestamp}
                </div>
              </div>
              <button
                onClick={() =>
                  onReplay({
                    type: n.type,
                    title: n.title,
                    message: n.message,
                    duration: n.duration,
                    tag: n.tag,
                  })
                }
                style={{
                  fontSize: "10px",
                  fontWeight: 700,
                  padding: "3px 9px",
                  borderRadius: "20px",
                  border: `1px solid ${cfg.icon_bg}30`,
                  background: `${cfg.icon_bg}12`,
                  color: cfg.icon_bg,
                  cursor: "pointer",
                  fontFamily: "inherit",
                  flexShrink: 0,
                }}
              >
                Replay
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════
   CONTEXT
═══════════════════════════════════════════════ */
interface NotificationContextValue {
  push: (config: NotificationConfig) => string;
  toggleHistory: () => void;
  position: NotificationPosition;
  setPosition: (pos: NotificationPosition) => void;
}

const NotificationContext = createContext<NotificationContextValue | null>(
  null
);

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notifs, setNotifs] = useState<Notification[]>([]);
  const [history, setHistory] = useState<Notification[]>(() => loadHistory());
  const [position, setPositionState] = useState<NotificationPosition>(() =>
    loadPosition()
  );
  const [editing, setEditing] = useState<Notification | null>(null);
  const [showLog, setShowLog] = useState(false);

  const setPosition = useCallback((pos: NotificationPosition) => {
    setPositionState(pos);
    savePosition(pos);
  }, []);

  useEffect(() => {
    saveHistory(history);
  }, [history]);

  const push = useCallback((cfg: NotificationConfig) => {
    const n: Notification = {
      ...cfg,
      id: mkId(),
      pinned: false,
      timestamp: new Date().toLocaleTimeString(),
    };
    setNotifs((p) => [...p, n]);
    setHistory((p) => [...p.slice(-(MAX_HISTORY - 1)), n]);
    return n.id;
  }, []);

  const dismiss = useCallback(
    (id: string) => setNotifs((p) => p.filter((n) => n.id !== id)),
    []
  );

  const pin = useCallback(
    (id: string) =>
      setNotifs((p) =>
        p.map((n) => (n.id === id ? { ...n, pinned: !n.pinned } : n))
      ),
    []
  );

  const editSave = useCallback((updated: Notification) => {
    setNotifs((p) => p.map((n) => (n.id === updated.id ? updated : n)));
    setEditing(null);
  }, []);

  const clearAll = useCallback(() => {
    setNotifs([]);
    setHistory([]);
  }, []);

  const toggleHistory = useCallback(() => {
    setShowLog((s) => !s);
  }, []);

  const value = useMemo<NotificationContextValue>(
    () => ({
      push,
      toggleHistory,
      position,
      setPosition,
    }),
    [push, toggleHistory, position, setPosition]
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <NotifTray
        notifs={notifs}
        position={position}
        onDismiss={dismiss}
        onEdit={setEditing}
        onPin={pin}
      />
      {editing && (
        <EditModal
          notif={editing}
          onSave={editSave}
          onClose={() => setEditing(null)}
        />
      )}
      {showLog && (
        <HistoryDrawer
          all={history}
          onClear={clearAll}
          onReplay={push}
          onClose={() => setShowLog(false)}
        />
      )}
      <style>{`
        @keyframes fadeIn { from { opacity: 0 } to { opacity: 1 } }
        @keyframes popIn { from { opacity: 0; transform: scale(.95) translateY(8px) } to { opacity: 1; transform: scale(1) translateY(0) } }
        @keyframes slideInRight { from { opacity: 0; transform: translateX(40px) } to { opacity: 1; transform: translateX(0) } }
      `}</style>
    </NotificationContext.Provider>
  );
}

export function useNotification(): NotificationContextValue {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error("useNotification must be used within NotificationProvider");
  }
  return ctx;
}
