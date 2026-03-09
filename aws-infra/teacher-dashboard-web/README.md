# Studaxis Teacher Dashboard (AWS Amplify)

Cloud-based Teacher Dashboard UI for the Studaxis EdTech platform. Runs on AWS Amplify and connects to cloud data models.

## Onboarding flow (StudaxisTeacherDashboard.jsx reference)

1. **Welcome** — Intro, AI Quiz Generation, DynamoDB sync, Bedrock
2. **Profile** — Name, email, subject, grade
3. **School** — School name, city, board
4. **First Class** — Class name, expected students, class code (auto-generated)
5. **Done** — Summary, next steps

On completion, data is persisted locally and to backend when `VITE_TEACHER_BACKEND_URL` is set:
- **POST /api/teacher/auth** — Authenticate by Class Code (+ optional Teacher ID). Returns JWT.
- **POST /api/teacher/onboard** — Register teacher + create first class
- **GET /api/teacher/lookup?classCode=XXX** — Fetch teacher by class code (legacy)

After login, the JWT is stored in localStorage and sent via `Authorization: Bearer <token>` on all teacher API requests.

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

## Backend connection

Set `VITE_TEACHER_BACKEND_URL` to your FastAPI backend (e.g. `http://localhost:6782`) to enable:
- Onboarding sync: teacher profile + class saved to backend
- Login: POST `/api/teacher/auth` with `{ classCode, teacherId? }` → returns JWT + teacher
- Seed a test teacher: `python scripts/seed_teacher.py --backend http://localhost:6782`

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
