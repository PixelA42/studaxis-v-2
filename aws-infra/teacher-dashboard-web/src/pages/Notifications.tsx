import { useState } from 'react';
import { Icon } from '../components/icons/Icon';
import { GlassCard } from '../components/dashboard/GlassCard';
import { EmptyState } from '../components/shared/EmptyState';
import { useNavigate } from 'react-router-dom';

type NotifType = 'success' | 'info' | 'warn' | 'assignment' | 'sync';

interface NotificationItem {
  id: number;
  ts: string;
  read: boolean;
  title: string;
  body: string;
  type: NotifType;
}

const typeIcon: Record<NotifType, string> = {
  success: '✅',
  info: 'ℹ️',
  warn: '⚠️',
  assignment: '📤',
  sync: '🔁',
};

export function Notifications() {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<NotificationItem[]>(() => [
    {
      id: 1,
      ts: new Date(Date.now() - 3600000).toISOString(),
      read: false,
      title: 'Class Created',
      body: '"Physics XI-A" ready · Code: ABC123',
      type: 'success',
    },
    {
      id: 2,
      ts: new Date(Date.now() - 7200000).toISOString(),
      read: false,
      title: 'Quiz Generated',
      body: '"Newton\'s Laws" saved to S3 · Ready to assign',
      type: 'success',
    },
    {
      id: 3,
      ts: new Date(Date.now() - 86400000).toISOString(),
      read: true,
      title: 'Notes Generated',
      body: '"Thermodynamics" notes ready · Saved to S3',
      type: 'success',
    },
  ]);

  const unread = notifications.filter((n) => !n.read).length;

  const markAsRead = (id: number) => {
    setNotifications((p) => p.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  const markAllRead = () => {
    setNotifications((p) => p.map((n) => ({ ...n, read: true })));
  };

  const clearAll = () => {
    setNotifications([]);
  };

  return (
    <main id="main-content" className="page-notifications" role="main">
      <div className="page-header-flex">
        <div>
          <h1 className="page-title">Notifications</h1>
          <p className="page-sub">
            {unread} unread · Synced to student activity and AWS events
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          {unread > 0 && (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={markAllRead}
            >
              <Icon name="check" size={12} /> Mark all read
            </button>
          )}
          {notifications.length > 0 && (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={clearAll}
            >
              <Icon name="x" size={12} /> Clear all
            </button>
          )}
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => navigate('/quiz')}
          >
            <Icon name="plus" size={12} /> Generate Quiz
          </button>
        </div>
      </div>

      <div className="notifications-layout">
        <GlassCard className="notifications-list-card">
          {notifications.length === 0 ? (
            <EmptyState
              icon="🔔"
              title="No notifications yet"
              description="Quiz generation, student sync events, assignment completions, and class activity will appear here."
            />
          ) : (
            <ul className="notifications-list" role="list">
              {notifications.map((n) => (
                <li
                  key={n.id}
                  className={`notif-item ${n.read ? '' : 'notif-item--unread'}`}
                  onClick={() => markAsRead(n.id)}
                >
                  <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                    <span style={{ fontSize: 19 }} aria-hidden>
                      {typeIcon[n.type]}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div className="notif-item-title">{n.title}</div>
                      <div className="notif-item-body">{n.body}</div>
                      <div className="notif-item-meta">
                        {new Date(n.ts).toLocaleString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </div>
                    </div>
                    {!n.read && (
                      <div
                        style={{
                          width: 7,
                          height: 7,
                          borderRadius: '50%',
                          background: 'var(--sd-accent-blue)',
                          marginTop: 4,
                          flexShrink: 0,
                        }}
                        aria-hidden
                      />
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </GlassCard>

        <GlassCard className="notifications-sidebar-card">
          <div className="section-title">Notification Types</div>
          {[
            ['🔁', 'Student Sync', 'Student comes online and syncs progress'],
            ['📝', 'Quiz Completed', 'Student completes an assigned quiz'],
            ['📤', 'Content Pushed', 'Quiz or notes assigned to a class'],
            ['⚠️', 'At Risk Alert', 'Student scores drop below threshold'],
            ['✅', 'Content Generated', 'Bedrock finishes generating content'],
          ].map(([icon, t, d]) => (
            <div key={t} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 12 }}>
              <span style={{ fontSize: 17 }} aria-hidden>
                {icon}
              </span>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--sd-dark)' }}>{t}</div>
                <div style={{ fontSize: 11, color: 'var(--sd-grey)', marginTop: 2 }}>{d}</div>
              </div>
            </div>
          ))}
          <div className="notif-banner notif-info" style={{ marginTop: 12 }}>
            <div className="notif-banner-icon">🔔</div>
            <div className="notif-banner-text">
              <strong style={{ color: 'var(--sd-dark)' }}>Backend:</strong> Live alerts from student devices arrive
              via AWS AppSync. Connect in Settings to enable.
            </div>
          </div>
        </GlassCard>
      </div>
    </main>
  );
}
