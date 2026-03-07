/**
 * Teacher Insights — no sidebar; redirect or message for web portal.
 */

export function TeacherInsightsPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="ambient-glow" aria-hidden />
      <div className="relative z-10 glass-panel rounded-2xl border border-glass-border p-8 max-w-lg text-center">
        <h1 className="text-xl font-semibold text-primary">
          Teacher dashboard is available via web portal
        </h1>
        <p className="text-primary/70 mt-2 text-sm">
          This local Studaxis app is designed for student laptops. As a teacher,
          you can access the full dashboard from your browser.
        </p>
      </div>
    </div>
  );
}
