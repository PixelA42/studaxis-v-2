import React, { useState, useEffect, lazy, Suspense } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { AppStateProvider } from "./contexts/AppStateContext";
import { AuthProvider } from "./contexts/AuthContext";
import { PanicExamProvider } from "./contexts/PanicExamContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { FlashcardDeckProvider } from "./contexts/FlashcardDeckContext";
import { NotificationProvider } from "./contexts/NotificationContext";
import { DashboardLayout } from "./components/DashboardLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { OllamaLoadingScreen } from "./components/OllamaLoadingScreen";
import { LoadingSpinner } from "./components/LoadingSpinner";
import { checkOllamaPing } from "./services/api";

/* Critical path — eager load for first paint */
import { LandingPage } from "./pages/Landing";

/* Lazy-loaded — code-split by route */
const Auth = lazy(() => import("./components/Auth").then((m) => ({ default: m.Auth })));

/* Lazy-loaded pages */
const OnboardingFlow = lazy(() => import("./pages/OnboardingFlow").then((m) => ({ default: m.OnboardingFlow })));
const HomePage = lazy(() => import("./pages/Home").then((m) => ({ default: m.HomePage })));
const DashboardPage = lazy(() => import("./pages/Dashboard").then((m) => ({ default: m.DashboardPage })));
const ChatPage = lazy(() => import("./pages/Chat").then((m) => ({ default: m.ChatPage })));
const FlashcardsPage = lazy(() => import("./pages/Flashcards").then((m) => ({ default: m.FlashcardsPage })));
const QuizPage = lazy(() => import("./pages/Quiz").then((m) => ({ default: m.QuizPage })));
const TextbooksPage = lazy(() => import("./pages/Textbooks").then((m) => ({ default: m.TextbooksPage })));
const SettingsPage = lazy(() => import("./pages/Settings").then((m) => ({ default: m.SettingsPage })));
const PanicModePage = lazy(() => import("./pages/PanicMode").then((m) => ({ default: m.PanicModePage })));
const InsightsPage = lazy(() => import("./pages/Insights").then((m) => ({ default: m.InsightsPage })));
const ConflictsPage = lazy(() => import("./pages/Conflicts").then((m) => ({ default: m.ConflictsPage })));
const ProfilePage = lazy(() => import("./pages/Profile").then((m) => ({ default: m.ProfilePage })));
const SyncPage = lazy(() => import("./pages/Sync").then((m) => ({ default: m.SyncPage })));
const TeacherInsightsPage = lazy(() => import("./pages/TeacherInsights").then((m) => ({ default: m.TeacherInsightsPage })));
const ErrorDemoPage = lazy(() => import("./pages/ErrorDemo").then((m) => ({ default: m.ErrorDemoPage })));
const VerifyEmailPage = lazy(() => import("./pages/VerifyEmail").then((m) => ({ default: m.VerifyEmailPage })));
const VerifyOTP = lazy(() => import("./pages/VerifyOTP").then((m) => ({ default: m.VerifyOTP })));

const PageFallback = () => (
  <div className="min-h-[40vh] flex items-center justify-center">
    <LoadingSpinner message="Loading…" />
  </div>
);

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
  return <Suspense fallback={<PageFallback />}>{children}</Suspense>;
}

function AppRoutes() {
  const navigate = useNavigate();
  return (
    <Suspense fallback={<PageFallback />}>
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/auth" element={<Auth />} />
      <Route path="/auth/login" element={<Auth />} />
      <Route path="/auth/signup" element={<Auth />} />
      <Route path="/login" element={<OnboardingFlow onComplete={() => navigate("/dashboard", { replace: true })} />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/verify-otp" element={<VerifyOTP />} />
      <Route path="/onboarding" element={<OnboardingFlow startFrom="role" onComplete={() => navigate("/dashboard", { replace: true })} />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/teacher-insights" element={<TeacherInsightsPage />} />
        <Route path="/error-demo" element={<ErrorDemoPage />} />
        <Route element={<DashboardLayout />}>
          <Route path="/home" element={<HomePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/flashcards" element={<FlashcardsPage />} />
          <Route path="/quiz" element={<QuizPage />} />
          <Route path="/textbooks" element={<TextbooksPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/panic-mode" element={<PanicModePage />} />
          <Route path="/insights" element={<InsightsPage />} />
          <Route path="/conflicts" element={<ConflictsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/sync" element={<SyncPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppStateProvider>
        <ThemeProvider>
          <FlashcardDeckProvider>
            <NotificationProvider>
              <PanicExamProvider>
                <BootGuard>
                  <AppRoutes />
                </BootGuard>
              </PanicExamProvider>
            </NotificationProvider>
          </FlashcardDeckProvider>
        </ThemeProvider>
      </AppStateProvider>
    </AuthProvider>
  );
}
