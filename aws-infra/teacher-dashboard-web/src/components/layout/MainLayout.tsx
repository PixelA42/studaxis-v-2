import { useState, useEffect, useRef } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Icon } from '../icons/Icon';
import { Sidebar } from './Sidebar';
import { NotificationBell } from './NotificationBell';
import { useTeacher } from '../../context/TeacherContext';

const NAV_LABELS: Record<string, string> = {
  '/': 'Overview',
  '/classes': 'Classes',
  '/students': 'Students',
  '/quiz': 'Quiz Generator',
  '/assignments': 'Assignments',
  '/sync': 'Sync Status',
  '/analytics': 'Analytics',
  '/settings': 'Settings',
};

function getCurrentLabel(pathname: string): string {
  for (const [path, label] of Object.entries(NAV_LABELS)) {
    if (path === '/' ? pathname === '/' : pathname.startsWith(path)) return label;
  }
  return 'Overview';
}

export function MainLayout() {
  const { teacher } = useTeacher();
  const navigate = useNavigate();
  const location = useLocation();
  const [sideOpen, setSideOpen] = useState(true);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    contentRef.current?.scrollTo(0, 0);
  }, [location.pathname]);

  const currentLabel = getCurrentLabel(location.pathname);
  const teacherName = teacher?.name || 'Teacher';
  const teacherSubject = teacher?.subject || 'Subject';

  return (
    <div className="app-root app-root--dashboard">
      <aside
        className={`app-sidebar ${!sideOpen ? 'app-sidebar--collapsed' : ''}`}
        style={{
          width: sideOpen ? 240 : 64,
          transition: 'width 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      >
        <Sidebar collapsed={!sideOpen} />

        {sideOpen && teacher && (
          <div className="sidebar-footer">
            <div className="sidebar-footer-teacher">
              <div className="sidebar-footer-avatar">
                {teacherName[0]?.toUpperCase() ?? 'T'}
              </div>
              <div className="sidebar-footer-info">
                <div className="sidebar-footer-name">{teacherName}</div>
                <div className="sidebar-footer-subject">{teacherSubject}</div>
              </div>
            </div>
          </div>
        )}

        <button
          type="button"
          className="sidebar-collapse-btn"
          onClick={() => setSideOpen((p) => !p)}
          aria-label={sideOpen ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          <Icon name={sideOpen ? 'arrow_left' : 'arrow_right'} size={12} color="var(--sd-grey)" />
        </button>
      </aside>

      <div className="app-main-content">
        <header className="dashboard-header">
          <div>
            <span className="dashboard-header-title">{currentLabel}</span>
            <span className="dashboard-header-date">
              {new Date().toLocaleDateString('en-IN', {
                weekday: 'long',
                day: 'numeric',
                month: 'long',
              })}
            </span>
          </div>
          <div className="dashboard-header-actions">
            <div className="chip chip-green">
              <span className="chip-dot chip-dot--green" />
              AWS Connected
            </div>
            <div className="dashboard-header-bell">
              <NotificationBell />
            </div>
            <button
              type="button"
              className="btn btn-primary dashboard-gen-btn"
              onClick={() => navigate('/quiz')}
            >
              <Icon name="plus" size={14} /> Generate Quiz
            </button>
          </div>
        </header>

        <div ref={contentRef} className="app-content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
