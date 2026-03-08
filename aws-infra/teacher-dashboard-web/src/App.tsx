import { BrowserRouter, Routes, Route, Navigate, useLocation, Link } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { TeacherProvider, useTeacher } from './context/TeacherContext';
import { Onboarding } from './pages/Onboarding';
import { Login } from './pages/Login';
import { MainLayout } from './components/layout/MainLayout';
import { DashboardOverview } from './pages/DashboardOverview';
import { Classes } from './pages/Classes';
import { Students } from './pages/Students';
import { Analytics } from './pages/Analytics';
import { QuizGenerator } from './pages/QuizGenerator';
import { Assignments } from './pages/Assignments';
import { SyncStatus } from './pages/SyncStatus';
import { Settings } from './pages/Settings';
import './styles/design-tokens.css';
import './styles/App.css';
import './styles/onboarding.css';

const PROTECTED_PATHS = ['/', '/classes', '/students', '/analytics', '/quiz', '/assignments', '/sync', '/settings'];

function RouteGuard({ children }: { children: React.ReactNode }) {
  const { teacher } = useTeacher();
  const location = useLocation();
  const path = location.pathname;
  const isProtected = PROTECTED_PATHS.some((p) => path === p || (p !== '/' && path.startsWith(p)));
  const hasClassCode = !!(teacher?.classCode?.trim());

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
        <Routes>
          <Route path="/login" element={<Login onComplete={completeOnboarding} />} />
          <Route path="/onboard" element={<Onboarding onComplete={completeOnboarding} signInLink={<Link to="/login" className="btn btn-ghost" style={{ padding: '4px 8px', fontSize: 12 }}>Sign In →</Link>} />} />
          <Route path="*" element={<Navigate to="/onboard" replace />} />
        </Routes>
      </BrowserRouter>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="/" element={<RouteGuard><MainLayout /></RouteGuard>}>
          <Route index element={<DashboardOverview />} />
          <Route path="classes" element={<Classes />} />
          <Route path="students" element={<Students />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="quiz" element={<QuizGenerator />} />
          <Route path="assignments" element={<Assignments />} />
          <Route path="sync" element={<SyncStatus />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
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
