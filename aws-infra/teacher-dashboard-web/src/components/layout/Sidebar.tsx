import { NavLink, useLocation } from 'react-router-dom';
import { Icon } from '../icons/Icon';

interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: 'home' | 'chart' | 'users' | 'book' | 'quiz' | 'check' | 'sync' | 'settings' | 'class';
}

const NAV_ITEMS: NavItem[] = [
  { id: 'overview', label: 'Overview', path: '/', icon: 'home' },
  { id: 'classes', label: 'Classes', path: '/classes', icon: 'class' },
  { id: 'students', label: 'Students', path: '/students', icon: 'users' },
  { id: 'quiz', label: 'Quiz Generator', path: '/quiz', icon: 'quiz' },
  { id: 'assignments', label: 'Assignments', path: '/assignments', icon: 'check' },
  { id: 'sync', label: 'Sync Status', path: '/sync', icon: 'sync' },
  { id: 'analytics', label: 'Analytics', path: '/analytics', icon: 'chart' },
  { id: 'settings', label: 'Settings', path: '/settings', icon: 'settings' },
];

interface SidebarProps {
  collapsed?: boolean;
}

export function Sidebar({ collapsed = false }: SidebarProps) {
  const location = useLocation();

  return (
    <nav className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''}`} aria-label="Main navigation">
      <div className="sidebar__brand">
        <span className="sidebar__logo">📐</span>
        {!collapsed && (
          <div>
            <span className="sidebar__title">Studaxis</span>
            <span className="sidebar__subtitle">Teacher Dashboard</span>
          </div>
        )}
      </div>

      <div className="sidebar__menu-label">Menu</div>
      <ul className="sidebar__nav" role="list">
        {NAV_ITEMS.map((item) => {
          const isActive = item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path);
          return (
            <li key={item.id}>
              <NavLink
                to={item.path}
                end={item.path === '/'}
                className={`sidebar__link ${isActive ? 'sidebar__link--active' : ''}`}
              >
                <Icon name={item.icon} size={18} color={isActive ? 'var(--sd-accent-pink)' : 'var(--sd-grey)'} />
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
