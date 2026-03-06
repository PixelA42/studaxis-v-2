import { NavLink } from 'react-router-dom';
import type { NavItemId } from '../../types';

interface NavItem {
  id: NavItemId;
  label: string;
  path: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard Overview', path: '/', icon: '📊' },
  { id: 'classes', label: 'Classes', path: '/classes', icon: '🏫' },
  { id: 'students', label: 'Students', path: '/students', icon: '👥' },
  { id: 'analytics', label: 'Analytics', path: '/analytics', icon: '📈' },
  { id: 'settings', label: 'Settings', path: '/settings', icon: '⚙️' },
];

export function Sidebar() {
  return (
    <nav className="sidebar" aria-label="Main navigation">
      <div className="sidebar__brand">
        <span className="sidebar__logo">🎓</span>
        <div>
          <span className="sidebar__title">Teacher Dashboard</span>
          <span className="sidebar__subtitle">v1.0</span>
        </div>
      </div>

      <ul className="sidebar__nav" role="list">
        {NAV_ITEMS.map((item) => (
          <li key={item.id}>
            <NavLink
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `sidebar__link ${isActive ? 'sidebar__link--active' : ''}`
              }
            >
              <span className="sidebar__link-icon" aria-hidden="true">
                {item.icon}
              </span>
              <span>{item.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
