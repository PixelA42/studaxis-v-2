# Studaxis Teacher Dashboard (AWS Amplify)

Cloud-based Teacher Dashboard UI for the Studaxis EdTech platform. Runs on AWS Amplify and connects to cloud data models.

## Onboarding flow (StudaxisTeacherDashboard.jsx reference)

1. **Welcome** — Intro, AI Quiz Generation, DynamoDB sync, Bedrock
2. **Profile** — Name, email, subject, grade
3. **School** — School name, city, board
4. **First Class** — Class name, expected students, class code (auto-generated)
5. **Done** — Summary, next steps

On completion, data is persisted locally and optionally to backend when `VITE_TEACHER_BACKEND_URL` is set (`POST /api/teacher/onboard`).

## Features

- **Layout**: Top navigation bar, sidebar, Bento-style modular grid
- **Dashboard modules**: Total Classes, Active Students, Assignment Completion Rate, Recent Activity, Performance Trends, Cloud Sync Status
- **Analytics**: Class selector, date range filters, export button (UI only), graph placeholders
- **Cloud Sync**: Status badge (Connected/Syncing/Error), last sync timestamp, manual sync trigger (UI only), error state card
- **State management**: Loading skeletons, empty states, error states, role-based (Teacher) rendering
- **Design system**: 70/20/8/2 color balance, glass cards, WCAG AA contrast, keyboard accessible, dark mode

## Run locally

```bash
npm install
npm run dev
```

## Build for Amplify

```bash
npm run build
```

Output in `dist/` for Amplify static hosting.

## Component Structure

```
src/
├── components/
│   ├── layout/        TopNav, Sidebar, MainLayout
│   ├── dashboard/     GlassCard, MetricTile, CloudSyncStatus
│   ├── analytics/     AnalyticsFilters, GraphPlaceholder, ExportButton
│   ├── sync/          SyncStatusBadge, SyncErrorCard, ManualSyncButton
│   └── shared/        Skeleton, EmptyState
├── pages/             DashboardOverview, Classes, Students, Analytics, Settings
├── context/           ThemeContext
├── types/             Type definitions
└── styles/            design-tokens.css, App.css
```
