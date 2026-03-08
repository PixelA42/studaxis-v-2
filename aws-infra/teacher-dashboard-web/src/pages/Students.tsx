import { useEffect, useState } from 'react';
import { GlassCard } from '../components/dashboard/GlassCard';
import { useTeacher } from '../context/TeacherContext';
import { listStudentProgresses, type StudentProgress } from '../lib/appsync';

function formatSyncStatus(lastSync: string | null): string {
  if (!lastSync) return 'Offline';
  const hours = (Date.now() - new Date(lastSync).getTime()) / (1000 * 60 * 60);
  if (hours < 1) return 'Synced';
  if (hours < 24) return 'Recent';
  return 'Pending';
}

function formatLastSync(ts: string | null): string {
  if (!ts) return '—';
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

export function Students() {
  const { teacher } = useTeacher();
  const classCode = teacher?.classCode ?? '';
  const [students, setStudents] = useState<StudentProgress[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'Synced' | 'Recent' | 'Pending' | 'Offline'>('all');

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    listStudentProgresses(classCode || '')
      .then((items) => {
        if (mounted) setStudents(items);
      })
      .catch((e) => {
        if (mounted) setError(e instanceof Error ? e.message : 'Failed to load students');
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => { mounted = false; };
  }, [classCode]);

  const filtered = students.filter((s) => {
    const matchSearch = !search.trim() ||
      s.user_id.toLowerCase().includes(search.toLowerCase()) ||
      (s.class_code ?? '').toLowerCase().includes(search.toLowerCase());
    const status = formatSyncStatus(s.last_sync_timestamp);
    const matchStatus = statusFilter === 'all' || status === statusFilter;
    return matchSearch && matchStatus;
  });

  return (
    <main id="main-content" className="page-students" role="main">
      <div className="page-header-block">
        <h1 className="page-title">Students</h1>
        <p className="page-sub">
          Live student progress from DynamoDB via AWS AppSync · Filtered by class code {classCode || '—'}.
        </p>
      </div>

      <GlassCard className="students-filters">
        <input
          className="input"
          style={{ maxWidth: 320 }}
          placeholder="🔍  Search students by ID or class..."
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className="select" style={{ maxWidth: 180 }} value={classCode || 'all'} disabled>
          <option>Class: {classCode || '—'}</option>
        </select>
        <select
          className="select"
          style={{ maxWidth: 180 }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
        >
          <option value="all">All Status</option>
          <option value="Synced">Synced</option>
          <option value="Recent">Recent</option>
          <option value="Pending">Pending</option>
          <option value="Offline">Offline</option>
        </select>
      </GlassCard>

      {error && (
        <div className="notif-banner notif-error" style={{ marginBottom: 16 }}>
          <div className="notif-banner-icon">⚠️</div>
          <div>
            <div className="notif-banner-title">AppSync Error</div>
            <div className="notif-banner-text">{error}</div>
          </div>
        </div>
      )}

      <GlassCard>
        <table className="students-table">
          <thead>
            <tr>
              <th>Student ID</th>
              <th>Class</th>
              <th>Streak</th>
              <th>Last Quiz</th>
              <th>Last Sync</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6}>
                  <div className="empty-state">
                    <div className="spinner" style={{ margin: '0 auto 12px' }} />
                    <div className="empty-state__title">Loading students...</div>
                    <div className="empty-state__description">Fetching from AppSync</div>
                  </div>
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className="empty-state">
                    <div className="empty-state__icon">👥</div>
                    <div className="empty-state__title">
                      {students.length === 0 ? 'No students synced yet' : 'No students match filters'}
                    </div>
                    <div className="empty-state__description">
                      {students.length === 0 ? (
                        <>
                          Share your class code {classCode && <strong>{classCode}</strong>} with students. Their progress will appear here after they sync via AWS AppSync.
                        </>
                      ) : (
                        'Try adjusting your search or status filter.'
                      )}
                    </div>
                  </div>
                </td>
              </tr>
            ) : (
              filtered.map((s) => (
                <tr key={s.user_id}>
                  <td><code style={{ fontSize: 12 }}>{s.user_id}</code></td>
                  <td>{s.class_code ?? classCode ?? '—'}</td>
                  <td>{s.current_streak ?? 0}</td>
                  <td>{s.last_quiz_date ? new Date(s.last_quiz_date).toLocaleDateString() : '—'}</td>
                  <td>{formatLastSync(s.last_sync_timestamp)}</td>
                  <td>
                    <span className={`chip chip-${formatSyncStatus(s.last_sync_timestamp) === 'Synced' ? 'green' : formatSyncStatus(s.last_sync_timestamp) === 'Recent' ? 'blue' : 'grey'}`}>
                      {formatSyncStatus(s.last_sync_timestamp)}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </GlassCard>
    </main>
  );
}
