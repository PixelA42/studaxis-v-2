import { useMemo } from 'react';

interface SyncActivityItem {
  id: string;
  studentName: string;
  action: string;
  timestamp: string;
  type: 'quiz' | 'streak' | 'content' | 'sync';
}

interface RecentSyncActivityProps {
  activities: SyncActivityItem[];
  maxItems?: number;
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    
    if (diffMs < 60000) return 'Just now';
    if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}m ago`;
    if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)}h ago`;
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return 'Unknown';
  }
}

function getActivityIcon(type: SyncActivityItem['type']): string {
  const icons = {
    quiz: '📝',
    streak: '🔥',
    content: '📚',
    sync: '🔄',
  };
  return icons[type];
}

export function RecentSyncActivity({ activities, maxItems = 10 }: RecentSyncActivityProps) {
  const displayedActivities = useMemo(
    () =>
      activities.slice(0, maxItems).map((activity) => ({
        ...activity,
        formattedTimestamp: formatTimestamp(activity.timestamp),
      })),
    [activities, maxItems]
  );

  return (
    <div className="recent-sync-activity">
      <h3 className="recent-sync-activity__title">Recent Sync Activity</h3>
      <p className="recent-sync-activity__subtitle">
        Latest student device synchronizations
      </p>

      {displayedActivities.length === 0 ? (
        <div className="recent-sync-activity__empty" role="status">
          <span className="recent-sync-activity__empty-icon" aria-hidden="true">
            📡
          </span>
          <p className="recent-sync-activity__empty-text">
            No recent activity
          </p>
        </div>
      ) : (
        <ul className="recent-sync-activity__list" role="list">
          {displayedActivities.map((activity) => (
            <li key={activity.id} className="recent-sync-activity__item">
              <span
                className="recent-sync-activity__icon"
                aria-hidden="true"
              >
                {getActivityIcon(activity.type)}
              </span>
              <div className="recent-sync-activity__content">
                <span className="recent-sync-activity__student">
                  {activity.studentName}
                </span>
                <span className="recent-sync-activity__action">
                  {activity.action}
                </span>
              </div>
              <time
                className="recent-sync-activity__time"
                dateTime={activity.timestamp}
              >
                {activity.formattedTimestamp}
              </time>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
