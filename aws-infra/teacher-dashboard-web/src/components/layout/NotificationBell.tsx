import { useMemo, useState } from 'react';

type NotificationStatus = 'read' | 'unread';
type NotificationPriority = 'low' | 'medium' | 'high';

interface NotificationItem {
  id: string;
  icon: string;
  category: string;
  message: string;
  timestamp: string;
  status: NotificationStatus;
  priority: NotificationPriority;
  studentName: string;
  event: string;
  details: string;
}

const PLACEHOLDER_UNREAD_COUNT = '[UNREAD_COUNT]';
const PLACEHOLDER_MESSAGE = '[NOTIFICATION_MESSAGE]';
const PLACEHOLDER_TIMESTAMP = '[NOTIFICATION_TIMESTAMP]';
const PLACEHOLDER_EVENT = '[NOTIFICATION_EVENT]';
const PLACEHOLDER_STUDENT_NAME = '[STUDENT_NAME]';

const PLACEHOLDER_TEACHER_NOTIFICATIONS: NotificationItem[] = [
  {
    id: 'teacher-notification-student-joined',
    icon: '👤',
    category: 'New student joined class',
    message: PLACEHOLDER_MESSAGE,
    timestamp: PLACEHOLDER_TIMESTAMP,
    status: 'unread',
    priority: 'medium',
    studentName: PLACEHOLDER_STUDENT_NAME,
    event: PLACEHOLDER_EVENT,
    details: 'Student enrollment notification detail: [NOTIFICATION_EVENT]',
  },
  {
    id: 'teacher-notification-quiz-completed',
    icon: '📘',
    category: 'Student completed quiz',
    message: PLACEHOLDER_MESSAGE,
    timestamp: PLACEHOLDER_TIMESTAMP,
    status: 'unread',
    priority: 'medium',
    studentName: PLACEHOLDER_STUDENT_NAME,
    event: PLACEHOLDER_EVENT,
    details: 'Quiz completion detail placeholder for teacher review.',
  },
  {
    id: 'teacher-notification-sync-pending',
    icon: '🔄',
    category: 'Sync pending from student device',
    message: PLACEHOLDER_MESSAGE,
    timestamp: PLACEHOLDER_TIMESTAMP,
    status: 'unread',
    priority: 'high',
    studentName: PLACEHOLDER_STUDENT_NAME,
    event: PLACEHOLDER_EVENT,
    details: 'Pending sync detail placeholder for student device.',
  },
  {
    id: 'teacher-notification-submission',
    icon: '📥',
    category: 'Assignment submissions',
    message: PLACEHOLDER_MESSAGE,
    timestamp: PLACEHOLDER_TIMESTAMP,
    status: 'read',
    priority: 'high',
    studentName: PLACEHOLDER_STUDENT_NAME,
    event: PLACEHOLDER_EVENT,
    details: 'Assignment submission detail placeholder for this class.',
  },
  {
    id: 'teacher-notification-weekly-summary',
    icon: '📊',
    category: 'Weekly progress summary available',
    message: PLACEHOLDER_MESSAGE,
    timestamp: PLACEHOLDER_TIMESTAMP,
    status: 'read',
    priority: 'low',
    studentName: PLACEHOLDER_STUDENT_NAME,
    event: PLACEHOLDER_EVENT,
    details: 'Weekly progress summary placeholder for teacher dashboard.',
  },
];

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>(PLACEHOLDER_TEACHER_NOTIFICATIONS);

  const unreadCount = useMemo(
    () => items.reduce((count, item) => count + (item.status === 'unread' ? 1 : 0), 0),
    [items]
  );

  function markAsRead(itemId: string) {
    setItems((prev) =>
      prev.map((item) => (item.id === itemId ? { ...item, status: 'read' } : item))
    );
  }

  function clearAll() {
    setItems([]);
  }

  return (
    <div className="notification-bell" data-open={isOpen ? 'true' : 'false'}>
      <button
        type="button"
        className="notification-bell__button"
        aria-label="Notifications"
        title="Notifications"
        onClick={() => setIsOpen((current) => !current)}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
      >
        <span className="notification-bell__icon" aria-hidden="true">
          🔔
        </span>
        <span className="notification-bell__count" aria-label={`Unread notifications: ${unreadCount}`}>
          {PLACEHOLDER_UNREAD_COUNT}
        </span>
      </button>

      {isOpen && (
        <section className="notification-panel" role="dialog" aria-label="Notifications panel">
          <header className="notification-panel__header">
            <div>
              <p className="notification-panel__eyebrow">Notifications</p>
              <h2 className="notification-panel__title">Teacher Notifications</h2>
            </div>
            <button
              type="button"
              className="notification-panel__clear-btn"
              onClick={clearAll}
              disabled={items.length === 0}
            >
              Clear all notifications
            </button>
          </header>

          {items.length === 0 ? (
            <div className="notification-empty-state" role="status" aria-live="polite">
              <div
                className="notification-empty-state__illustration"
                aria-label="Empty State Illustration Placeholder"
              >
                Empty State Illustration Placeholder
              </div>
              <p className="notification-empty-state__title">You&apos;re all caught up!</p>
              <p className="notification-empty-state__hint">
                New updates will appear here when notification data is available.
              </p>
            </div>
          ) : (
            <ul className="notification-panel__list">
              {items.map((item) => {
                const isUnread = item.status === 'unread';
                return (
                  <li key={item.id} className="notification-panel__list-item">
                    <article
                      className={`notification-card notification-card--${item.priority} ${
                        isUnread ? 'notification-card--unread' : ''
                      }`}
                    >
                      <div className="notification-card__top">
                        <div className="notification-card__icon" aria-label={`${item.category} icon`}>
                          {item.icon}
                        </div>
                        <div className="notification-card__body">
                          <p className="notification-card__category">{item.category}</p>
                          <p className="notification-card__message">{item.message}</p>
                          <p className="notification-card__meta-line">
                            <strong>Student:</strong> {item.studentName}
                          </p>
                          <p className="notification-card__meta-line">
                            <strong>Event:</strong> {item.event}
                          </p>
                          <p className="notification-card__timestamp">
                            Time: {item.timestamp === '' ? PLACEHOLDER_TIMESTAMP : item.timestamp}
                          </p>
                        </div>
                        <span
                          className={`notification-card__status notification-card__status--${item.status}`}
                          aria-label={`Notification status: ${item.status}`}
                        >
                          {item.status}
                        </span>
                      </div>

                      <div className="notification-card__actions">
                        <button
                          type="button"
                          className="notification-card__action-btn"
                          onClick={() => markAsRead(item.id)}
                          disabled={!isUnread}
                        >
                          {isUnread ? 'Mark notification as read' : 'Marked as read'}
                        </button>
                        <details className="notification-card__details">
                          <summary>Expand notification details</summary>
                          <p>{item.details}</p>
                        </details>
                      </div>
                    </article>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
