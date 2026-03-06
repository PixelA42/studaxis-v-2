import { useState, useRef, useEffect } from 'react';
import { useTheme } from '../../context/ThemeContext';
import type { SyncStatus } from '../../types';
import { SyncStatusBadge } from '../sync/SyncStatusBadge';
import { NotificationBell } from './NotificationBell';

interface TopNavProps {
  teacherName: string;
  syncStatus: SyncStatus;
  lastSyncTimestamp: string | null;
}

export function TopNav({ teacherName, syncStatus, lastSyncTimestamp }: TopNavProps) {
  const { theme, toggleTheme } = useTheme();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, []);

  return (
    <header className="top-nav" role="banner">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <div className="top-nav__inner">
        <div className="top-nav__brand">
          <span className="top-nav__logo" aria-hidden="true">🎓</span>
          <span className="top-nav__app-name">Studaxis</span>
        </div>

        <div className="top-nav__right">
          <SyncStatusBadge
            status={syncStatus}
            lastSyncTimestamp={lastSyncTimestamp}
            size="compact"
          />

          <NotificationBell />

          <div className="top-nav__profile-wrap" ref={dropdownRef}>
            <button
              type="button"
              className="top-nav__profile"
              onClick={() => setDropdownOpen(!dropdownOpen)}
              aria-expanded={dropdownOpen}
              aria-haspopup="true"
              aria-label="Teacher profile menu"
            >
              <span className="top-nav__avatar" aria-hidden="true">
                {teacherName.slice(0, 2).toUpperCase()}
              </span>
              <span className="top-nav__name">{teacherName}</span>
              <span className="top-nav__chevron" aria-hidden="true">▼</span>
            </button>

            {dropdownOpen && (
              <div
                className="top-nav__dropdown"
                aria-label="Profile menu"
              >
                <a href="#profile" className="top-nav__dropdown-item" onClick={() => setDropdownOpen(false)}>
                  Profile
                </a>
                <a href="#account" className="top-nav__dropdown-item" onClick={() => setDropdownOpen(false)}>
                  Account
                </a>
                <button
                  type="button"
                  className="top-nav__dropdown-item"
                  onClick={() => {
                    toggleTheme();
                    setDropdownOpen(false);
                  }}
                >
                  {theme === 'light' ? 'Dark mode' : 'Light mode'}
                </button>
                <hr className="top-nav__dropdown-divider" />
                <a href="#logout" className="top-nav__dropdown-item" onClick={() => setDropdownOpen(false)}>
                  Sign out
                </a>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
