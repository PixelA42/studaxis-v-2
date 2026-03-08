import { GlassCard } from '../components/dashboard/GlassCard';

export function Students() {
  const students: { id: string; name: string; class: string; streak: number; quizAvg: number; lastSync: string; status: string }[] = [];

  return (
    <main id="main-content" className="page-students" role="main">
      <div className="page-header-block">
        <h1 className="page-title">Students</h1>
        <p className="page-sub">Student progress syncs from DynamoDB when they come online.</p>
      </div>

      <GlassCard className="students-filters">
        <input
          className="input"
          style={{ maxWidth: 320 }}
          placeholder="🔍  Search students by name or email..."
          type="search"
        />
        <select className="select" style={{ maxWidth: 180 }}>
          <option>All Classes</option>
        </select>
        <select className="select" style={{ maxWidth: 180 }}>
          <option>All Status</option>
          <option>Synced</option>
          <option>Pending</option>
          <option>Offline</option>
        </select>
      </GlassCard>

      <GlassCard>
        <table className="students-table">
          <thead>
            <tr>
              <th>Student</th>
              <th>Class</th>
              <th>Streak</th>
              <th>Quiz Avg</th>
              <th>Last Sync</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {students.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className="empty-state">
                    <div className="empty-state__icon">👥</div>
                    <div className="empty-state__title">No students synced yet</div>
                    <div className="empty-state__description">
                      Share your class code with students. Their progress will appear here after they sync via AWS AppSync.
                    </div>
                  </div>
                </td>
              </tr>
            ) : (
              students.map((s) => (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td>{s.class}</td>
                  <td>{s.streak}</td>
                  <td>{s.quizAvg}%</td>
                  <td>{s.lastSync}</td>
                  <td>
                    <span className="chip chip-grey">{s.status}</span>
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
