import { Outlet } from 'react-router-dom';
import { TopNav } from './TopNav';
import { Sidebar } from './Sidebar';
import type { SyncStatus } from '../../types';

const TEACHER_NAME = 'Teacher'; // Placeholder — will come from auth
const SYNC_STATUS: SyncStatus = 'connected';
const LAST_SYNC = new Date().toISOString();

export function MainLayout() {
  return (
    <div className="app-root">
      <TopNav
        teacherName={TEACHER_NAME}
        syncStatus={SYNC_STATUS}
        lastSyncTimestamp={LAST_SYNC}
      />
      <div className="app-main">
        <aside className="app-sidebar">
          <Sidebar />
        </aside>
        <div className="app-content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
