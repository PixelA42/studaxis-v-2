import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { AppStateProvider, useAppState } from "./contexts/AppStateContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { FlashcardDeckProvider } from "./contexts/FlashcardDeckContext";
import { BootFlow } from "./pages/BootFlow";
import { LandingPage } from "./pages/Landing";
import { LoginPage } from "./pages/Login";
import { SignupPage } from "./pages/Signup";
import { DashboardPage } from "./pages/Dashboard";
import { ChatPage } from "./pages/Chat";
import { FlashcardsPage } from "./pages/Flashcards";
import { QuizPage } from "./pages/Quiz";
import { SettingsPage } from "./pages/Settings";
import { PanicModePage } from "./pages/PanicMode";
import { InsightsPage } from "./pages/Insights";
import { ConflictsPage } from "./pages/Conflicts";
import { ProfilePage } from "./pages/Profile";
import { SyncPage } from "./pages/Sync";
import { TeacherInsightsPage } from "./pages/TeacherInsights";
import { ErrorDemoPage } from "./pages/ErrorDemo";
import { DashboardLayout } from "./components/DashboardLayout";

function BootGuard({ children }: { children: React.ReactNode }) {
  const { bootComplete } = useAppState();
  const navigate = useNavigate();
  if (!bootComplete) {
    return (
      <BootFlow
        onComplete={() => navigate("/dashboard", { replace: true })}
      />
    );
  }
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/auth" element={<LoginPage />} />
      <Route path="/auth/login" element={<LoginPage />} />
      <Route path="/auth/signup" element={<SignupPage />} />
      <Route path="/teacher-insights" element={<TeacherInsightsPage />} />
      <Route path="/error-demo" element={<ErrorDemoPage />} />
      <Route element={<DashboardLayout />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/flashcards" element={<FlashcardsPage />} />
        <Route path="/quiz" element={<QuizPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/panic-mode" element={<PanicModePage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/conflicts" element={<ConflictsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/sync" element={<SyncPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppStateProvider>
        <ThemeProvider>
          <FlashcardDeckProvider>
            <BootGuard>
              <AppRoutes />
            </BootGuard>
          </FlashcardDeckProvider>
        </ThemeProvider>
      </AppStateProvider>
    </AuthProvider>
  );
}
