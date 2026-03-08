/**
 * NotificationTray — Slide-in panel from the right for notification history.
 * Shows notifications with type badges, pinned indicator, action links.
 * Backdrop click closes tray.
 */

import { useState } from "react";
import { Link } from "react-router-dom";
import { useNotification } from "../contexts/NotificationContext";
import type { Notification, NotificationType } from "../contexts/NotificationContext";
import { HiBell } from "react-icons/hi2";

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

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString();
  } catch {
    return iso;
  }
}

export function NotificationTray() {
  const {
    notifications,
    unreadCount,
    dismiss,
    markAllRead,
    closeTray,
    pin,
    clearAll,
  } = useNotification();

  return (
    <>
      {/* Backdrop — click outside closes tray */}
      <div
        role="presentation"
        aria-hidden
        onClick={closeTray}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.25)",
          zIndex: 199,
          animation: "fadeIn 0.2s ease",
        }}
      />
      <div
        role="dialog"
        aria-label="Notifications"
        style={{
          position: "fixed",
          right: 0,
          top: 0,
          height: "100vh",
          width: 360,
          background: "#ffffff",
          borderLeft: "1.5px solid #e8edf5",
          boxShadow: "-8px 0 32px rgba(0,0,0,0.1)",
          zIndex: 200,
          animation: "slideIn 0.3s cubic-bezier(0.16,1,0.3,1)",
          display: "flex",
          flexDirection: "column",
        }}
      >
      {/* Header */}
      <div
        style={{
          padding: "20px 18px 14px",
          borderBottom: "1px solid #e8edf5",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <h2
              style={{
                fontSize: 16,
                fontWeight: 700,
                color: "#0d1b2a",
                margin: 0,
                letterSpacing: "-0.3px",
              }}
            >
              Notifications
            </h2>
            {unreadCount > 0 && (
              <span
                style={{
                  background: "#FA5C5C",
                  color: "white",
                  borderRadius: "50%",
                  width: 18,
                  height: 18,
                  fontSize: 9,
                  fontWeight: 800,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button
              type="button"
              onClick={markAllRead}
              style={{
                padding: "6px 12px",
                border: "none",
                background: "transparent",
                fontSize: 12,
                fontWeight: 600,
                color: "#00a8e8",
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              Mark all read
            </button>
            <button
              type="button"
              onClick={closeTray}
              style={{
                width: 32,
                height: 32,
                border: "none",
                background: "transparent",
                color: "#9ca3af",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: 8,
              }}
              aria-label="Close"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* List */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px 14px",
        }}
      >
        {notifications.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "48px 24px",
              color: "#9ca3af",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                marginBottom: 16,
                color: "#d1d5db",
              }}
            >
              <HiBell className="w-12 h-12" style={{ width: 48, height: 48 }} />
            </div>
            <div
              style={{
                fontSize: 15,
                fontWeight: 700,
                color: "#6b7280",
                marginBottom: 8,
              }}
            >
              No notifications yet
            </div>
            <div
              style={{
                fontSize: 12,
                lineHeight: 1.5,
                color: "#9ca3af",
              }}
            >
              Quiz assignments, sync alerts and streak reminders will appear here
            </div>
          </div>
        ) : (
          <>
            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                marginBottom: 8,
              }}
            >
              <button
                type="button"
                onClick={clearAll}
                style={{
                  padding: "4px 10px",
                  borderRadius: 6,
                  border: "none",
                  background: "transparent",
                  fontSize: 11,
                  fontWeight: 600,
                  color: "#6b7280",
                  cursor: "pointer",
                }}
              >
                Clear all
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {notifications.map((n) => (
                <NotificationCard
                  key={n.id}
                  notif={n}
                  onDismiss={() => dismiss(n.id)}
                  onPin={() => pin(n.id)}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
    </>
  );
}

function NotificationCard({
  notif,
  onDismiss,
  onPin,
}: {
  notif: Notification;
  onDismiss: () => void;
  onPin: () => void;
}) {
  const [hover, setHover] = useState(false);
  const accent = ACCENT_COLORS[notif.type] ?? ACCENT_COLORS.info;

  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: "flex",
        flexDirection: "column",
        borderRadius: 12,
        border: "1px solid #e8edf5",
        overflow: "hidden",
        background: notif.read ? "#ffffff" : "#fafcff",
        position: "relative",
      }}
    >
      {/* Dismiss on hover — top right */}
      {hover && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDismiss();
          }}
          style={{
            position: "absolute",
            top: 8,
            right: 8,
            width: 24,
            height: 24,
            border: "none",
            background: "transparent",
            color: "#9ca3af",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            borderRadius: 6,
            zIndex: 1,
          }}
          aria-label="Dismiss"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      )}
      <div
        style={{
          display: "flex",
          borderLeft: `4px solid ${accent}`,
          padding: "12px 14px 12px 16px",
          gap: 10,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              marginBottom: 4,
            }}
          >
            <span
              style={{
                fontSize: 10,
                fontWeight: 800,
                color: accent,
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}
            >
              {notif.type}
            </span>
            {notif.pinned && (
              <span
                style={{ fontSize: 9, fontWeight: 700 }}
                title="Pinned"
              >
                📌
              </span>
            )}
            {notif.tag && (
              <span
                style={{
                  fontSize: 9,
                  fontWeight: 600,
                  background: "rgba(0,0,0,0.06)",
                  color: "#6b7280",
                  borderRadius: 10,
                  padding: "2px 6px",
                }}
              >
                {notif.tag}
              </span>
            )}
          </div>
          <div
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: "#0d1b2a",
              lineHeight: 1.3,
            }}
          >
            {notif.title}
          </div>
          {notif.message && (
            <div
              style={{
                fontSize: 12,
                color: "#6b7280",
                marginTop: 4,
                lineHeight: 1.5,
              }}
            >
              {notif.message}
            </div>
          )}
          <div
            style={{
              fontSize: 10,
              color: "#9ca3af",
              marginTop: 6,
            }}
          >
            {formatTime(notif.timestamp)}
          </div>
          {notif.action && (
            notif.action.href.startsWith("/") ? (
              <Link
                to={notif.action.href}
                style={{
                  display: "inline-block",
                  marginTop: 8,
                  padding: "5px 12px",
                  borderRadius: 8,
                  border: "none",
                  background: "transparent",
                  color: "#00a8e8",
                  fontSize: 11,
                  fontWeight: 700,
                  textDecoration: "none",
                  cursor: "pointer",
                }}
              >
                {notif.action.label}
              </Link>
            ) : (
              <a
                href={notif.action.href}
                style={{
                  display: "inline-block",
                  marginTop: 8,
                  padding: "5px 12px",
                  borderRadius: 8,
                  border: "none",
                  background: "transparent",
                  color: "#00a8e8",
                  fontSize: 11,
                  fontWeight: 700,
                  textDecoration: "none",
                  cursor: "pointer",
                }}
              >
                {notif.action.label}
              </a>
            )
          )}
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}
        >
          <button
            type="button"
            onClick={onPin}
            style={{
              width: 28,
              height: 28,
              border: "none",
              background: "transparent",
              color: notif.pinned ? accent : "#9ca3af",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 6,
            }}
            title={notif.pinned ? "Unpin" : "Pin"}
          >
            📌
          </button>
        </div>
      </div>
    </div>
  );
}
