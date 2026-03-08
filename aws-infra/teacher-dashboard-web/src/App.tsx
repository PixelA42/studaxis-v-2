import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { TeacherProvider, useTeacher } from './context/TeacherContext';
import { Onboarding } from './pages/Onboarding';
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

function AppContentWrapper() {
  const { teacher, completeOnboarding } = useTeacher();
  if (!teacher) {
    return <Onboarding onComplete={completeOnboarding} />;
  }
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
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
