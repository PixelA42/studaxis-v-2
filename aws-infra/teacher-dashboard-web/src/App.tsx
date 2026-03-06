import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { MainLayout } from './components/layout/MainLayout';
import { DashboardOverview } from './pages/DashboardOverview';
import { Classes } from './pages/Classes';
import { Students } from './pages/Students';
import { Analytics } from './pages/Analytics';
import { Settings } from './pages/Settings';
import './styles/design-tokens.css';
import './styles/App.css';

function AppContent() {
  useEffect(() => {
    document.documentElement.classList.add('theme-light');
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<DashboardOverview />} />
          <Route path="classes" element={<Classes />} />
          <Route path="students" element={<Students />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}
