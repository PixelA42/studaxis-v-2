import { useState, useEffect, useRef } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Icon } from '../icons/Icon';
import { Sidebar } from './Sidebar';
import { NotificationBell } from './NotificationBell';
import { useTeacher } from '../../context/TeacherContext';
import { useTheme } from '../../context/ThemeContext';

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

function getInitialSideOpen(): boolean {
  if (typeof window === 'undefined') return true;
  return window.innerWidth >= 768;
}

export function MainLayout() {
  const { teacher, logout } = useTeacher();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [sideOpen, setSideOpen] = useState(getInitialSideOpen);
  const [isMobile, setIsMobile] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  useEffect(() => {
    contentRef.current?.scrollTo(0, 0);
  }, [location.pathname]);

  const currentLabel = getCurrentLabel(location.pathname);
  const teacherName = teacher?.name || 'Teacher';
  const teacherSubject = teacher?.subject || 'Subject';

  const sidebarVisible = isMobile ? sideOpen : true;
  const marginLeft = isMobile
    ? 0
    : sideOpen
      ? 252
      : 88;

  return (
    <div
      className="app-root app-root--dashboard"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'var(--sd-bg)',
        overflow: 'hidden',
      }}
    >
      {/* Floating sidebar */}
      <aside
        className={`app-sidebar app-sidebar--floating ${!sideOpen ? 'app-sidebar--collapsed' : ''} ${!sidebarVisible ? 'app-sidebar--hidden' : ''}`}
        style={{
          position: 'fixed',
          top: 16,
          left: 16,
          bottom: 16,
          width: sideOpen ? 220 : 56,
          background: 'var(--sd-bg-glass)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          borderRadius: 20,
          border: '1.5px solid var(--sd-border-subtle)',
          boxShadow: 'var(--sd-shadow-card)',
          zIndex: 50,
          display: 'flex',
          flexDirection: 'column',
          transition: 'width 0.3s cubic-bezier(0.16,1,0.3,1), transform 0.25s ease',
          overflow: 'hidden',
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
            <button
              type="button"
              className="sidebar-footer-signout"
              onClick={() => logout()}
            >
              Sign out
            </button>
          </div>
        )}

        <button
          type="button"
          className="sidebar-collapse-btn-inner"
          onClick={() => setSideOpen((p) => !p)}
          aria-label={sideOpen ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          <Icon name={sideOpen ? 'arrow_left' : 'arrow_right'} size={16} color="var(--sd-grey)" />
          {sideOpen && <span>Collapse</span>}
        </button>
      </aside>

      {/* Full-width content area */}
      <div
        className="app-main-content"
        style={{
          position: 'fixed',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <header
          className="dashboard-header"
          style={{
            marginLeft: marginLeft,
            transition: 'margin-left 0.3s cubic-bezier(0.16,1,0.3,1)',
          }}
        >
          <div className="dashboard-header-left">
            {isMobile && (
              <button
                type="button"
                className="dashboard-hamburger"
                onClick={() => setSideOpen((p) => !p)}
                aria-label="Toggle menu"
              >
                <Icon name="menu" size={20} color="var(--sd-dark)" />
              </button>
            )}
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
          </div>
          <div className="dashboard-header-actions">
            <button
              type="button"
              onClick={toggleTheme}
              className="theme-toggle-btn"
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            >
              <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={18} color="var(--sd-grey)" />
            </button>
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

        <div
          ref={contentRef}
          className="app-content"
          style={{
            marginLeft: marginLeft,
            transition: 'margin-left 0.3s cubic-bezier(0.16,1,0.3,1)',
            flex: 1,
            overflow: 'auto',
            minHeight: 0,
            padding: 24,
          }}
        >
          <Outlet />
        </div>
      </div>

      {/* Mobile overlay when sidebar open */}
      {isMobile && sideOpen && (
        <div
          className="sidebar-backdrop"
          aria-hidden
          onClick={() => setSideOpen(false)}
        />
      )}
    </div>
  );
}
