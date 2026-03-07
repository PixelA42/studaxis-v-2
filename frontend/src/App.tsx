import React, { useState, useEffect } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { AppStateProvider, useAppState } from "./contexts/AppStateContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { FlashcardDeckProvider } from "./contexts/FlashcardDeckContext";
import { BootFlow } from "./pages/BootFlow";
import { LandingPage } from "./pages/Landing";
import { Auth } from "./components/Auth";
import { HomePage } from "./pages/Home";
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
import { OllamaLoadingScreen } from "./components/OllamaLoadingScreen";
import { checkOllamaPing } from "./services/api";

/** First thing when app opens: wait for Ollama to be ready, then show the app. */
export function OllamaGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (ready) return;
    const poll = async () => {
      try {
        const res = await checkOllamaPing();
        if (res.ok) setReady(true);
      } catch {
        // Backend or network unavailable; keep polling
      }
    };
    poll();
    const id = setInterval(poll, 1500);
    return () => clearInterval(id);
  }, [ready]);

  if (!ready) return <OllamaLoadingScreen onReady={() => setReady(true)} />;
  return <>{children}</>;
}

function BootGuard({ children }: { children: React.ReactNode }) {
  const { bootComplete } = useAppState();
  const navigate = useNavigate();
  if (!bootComplete) {
    return (
      <BootFlow
        onComplete={() => navigate("/home", { replace: true })}
      />
    );
  }
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/auth" element={<Auth />} />
      <Route path="/auth/login" element={<Auth />} />
      <Route path="/auth/signup" element={<Auth />} />
      <Route path="/teacher-insights" element={<TeacherInsightsPage />} />
      <Route path="/error-demo" element={<ErrorDemoPage />} />
      <Route element={<DashboardLayout />}>
        <Route path="/home" element={<HomePage />} />
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
