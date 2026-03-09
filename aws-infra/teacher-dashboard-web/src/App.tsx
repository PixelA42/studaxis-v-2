import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, Link } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { TeacherProvider, useTeacher } from './context/TeacherContext';
import { ClassProvider } from './context/ClassContext';
import { MainLayout } from './components/layout/MainLayout';
import './styles/design-tokens.css';
import './styles/App.css';
import './styles/onboarding.css';

const Onboarding = lazy(() => import('./pages/Onboarding').then((m) => ({ default: m.Onboarding })));
const Login = lazy(() => import('./pages/Login').then((m) => ({ default: m.Login })));
const DashboardOverview = lazy(() => import('./pages/DashboardOverview').then((m) => ({ default: m.DashboardOverview })));
const Classes = lazy(() => import('./pages/Classes').then((m) => ({ default: m.Classes })));
const Students = lazy(() => import('./pages/Students').then((m) => ({ default: m.Students })));
const Analytics = lazy(() => import('./pages/Analytics').then((m) => ({ default: m.Analytics })));
const QuizGenerator = lazy(() => import('./pages/QuizGenerator').then((m) => ({ default: m.QuizGenerator })));
const NotesGenerator = lazy(() => import('./pages/NotesGenerator').then((m) => ({ default: m.NotesGenerator })));
const Assignments = lazy(() => import('./pages/Assignments').then((m) => ({ default: m.Assignments })));
const Notifications = lazy(() => import('./pages/Notifications').then((m) => ({ default: m.Notifications })));
const SyncStatus = lazy(() => import('./pages/SyncStatus').then((m) => ({ default: m.SyncStatus })));
const Settings = lazy(() => import('./pages/Settings').then((m) => ({ default: m.Settings })));

const PageLoader = () => (
  <div className="flex items-center justify-center min-h-[200px]">
    <span className="loading loading-spinner loading-lg text-primary" />
  </div>
);
const PROTECTED_PATHS = ['/', '/classes', '/students', '/analytics', '/quiz', '/notes', '/assignments', '/sync', '/notifications', '/settings'];

function RouteGuard({ children }: { children: React.ReactNode }) {
  const { teacher } = useTeacher();
  const location = useLocation();
  const path = location.pathname;
  const isProtected = PROTECTED_PATHS.some((p) => path === p || (p !== '/' && path.startsWith(p)));
  const hasClassCode = !!(teacher?.classCode?.trim());

  // Allow access if teacher has classCode (legacy or multi-class)
  if (isProtected && !hasClassCode) {
    return <Navigate to="/login" replace state={{ from: path }} />;
  }
  return <>{children}</>;
}

function AppContentWrapper() {
  const { teacher, completeOnboarding } = useTeacher();
  const hasClassCode = !!(teacher?.classCode?.trim());

  if (!hasClassCode) {
    return (
      <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/login" element={<Login onComplete={completeOnboarding} />} />
            <Route path="/onboard" element={<Onboarding onComplete={completeOnboarding} signInLink={<Link to="/login" className="btn btn-ghost" style={{ padding: '4px 8px', fontSize: 12 }}>Sign In →</Link>} />} />
            <Route path="*" element={<Navigate to="/onboard" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    );
  }

  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/login" element={<Navigate to="/" replace />} />
          <Route path="/" element={<RouteGuard><ClassProvider><MainLayout /></ClassProvider></RouteGuard>}>
            <Route index element={<DashboardOverview />} />
            <Route path="classes" element={<Classes />} />
            <Route path="students" element={<Students />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="quiz" element={<QuizGenerator />} />
            <Route path="notes" element={<NotesGenerator />} />
            <Route path="assignments" element={<Assignments />} />
            <Route path="notifications" element={<Notifications />} />
            <Route path="sync" element={<SyncStatus />} />
            <Route path="settings" element={<Settings />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <TeacherProvider>
        <AppContentWrapper />
      </TeacherProvider>
    </ThemeProvider>
  );
}
