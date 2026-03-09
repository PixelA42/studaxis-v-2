import { NavLink, useLocation } from 'react-router-dom';
import { Icon } from '../icons/Icon';

interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: 'home' | 'chart' | 'users' | 'book' | 'quiz' | 'note' | 'check' | 'sync' | 'settings' | 'class' | 'bell';
}

const NAV_ITEMS: NavItem[] = [
  { id: 'overview', label: 'Overview', path: '/', icon: 'home' },
  { id: 'classes', label: 'Classes', path: '/classes', icon: 'class' },
  { id: 'students', label: 'Students', path: '/students', icon: 'users' },
  { id: 'quiz', label: 'Quiz Generator', path: '/quiz', icon: 'quiz' },
  { id: 'notes', label: 'Notes Generator', path: '/notes', icon: 'note' },
  { id: 'assignments', label: 'Assignments', path: '/assignments', icon: 'check' },
  { id: 'sync', label: 'Sync Status', path: '/sync', icon: 'sync' },
  { id: 'analytics', label: 'Analytics', path: '/analytics', icon: 'chart' },
  { id: 'notifications', label: 'Notifications', path: '/notifications', icon: 'bell' },
  { id: 'settings', label: 'Settings', path: '/settings', icon: 'settings' },
];

interface SidebarProps {
  collapsed?: boolean;
}

export function Sidebar({ collapsed = false }: SidebarProps) {
  const location = useLocation();

  return (
    <nav className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''}`} aria-label="Main navigation">
      <div className={`sidebar__brand ${collapsed ? 'sidebar__brand--collapsed' : ''}`}>
          <span className="sidebar__logo">
            {/* Studaxis logo PNG */}
            <img
              src={require("../../assets/studaxis-logo.png")}
              alt="Studaxis Logo"
              width={32}
              height={32}
              style={{ display: "block" }}
            />
          </span>
        {!collapsed && (
          <div>
            <span className="sidebar__title">Studaxis</span>
            <span className="sidebar__subtitle">Teacher Dashboard</span>
          </div>
        )}
      </div>

      <div className="sidebar__nav-wrap">
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
      </div>
    </nav>
  );
}
