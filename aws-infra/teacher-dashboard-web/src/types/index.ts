/**
 * Teacher Dashboard — Type definitions
 * UI structure and state only (no backend logic)
 */

export type SyncStatus = 'connected' | 'syncing' | 'error' | 'offline';

export type ThemeMode = 'light' | 'dark';

export interface SyncState {
  status: SyncStatus;
  lastSyncTimestamp: string | null;
  errorMessage?: string;
}

/**
 * Partial sync status — represents scenarios where only part of a
 * student's data payload has been synced (e.g. quiz data uploaded
 * but metadata not yet delivered).
 *
 * All values are placeholder-driven. No actual sync logic.
 */
export type PartialSyncStatus =
  | 'fully_synced'
  | 'data_only'
  | 'metadata_pending'
  | 'unknown';

export interface StudentSyncInfo {
  id: string;
  name: string;
  syncStatus: SyncStatus | string;
  lastSync: string | null;
  partialSyncStatus?: PartialSyncStatus;
}

export interface DashboardMetrics {
  totalClasses: number;
  activeStudents: number;
  assignmentCompletionRate: number;
  recentActivityCount: number;
}

export interface RecentActivityItem {
  id: string;
  studentName: string;
  action: string;
  timestamp: string;
}

export type NavItemId = 'dashboard' | 'classes' | 'students' | 'analytics' | 'settings';
