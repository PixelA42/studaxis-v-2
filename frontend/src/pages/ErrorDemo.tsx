/**
 * Error demo — no sidebar; placeholder for error UI demo.
 */

export function ErrorDemoPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="ambient-glow" aria-hidden />
      <div className="relative z-10 glass-panel rounded-2xl border border-glass-border p-8 max-w-lg text-center">
        <h1 className="text-xl font-semibold text-primary">Error Demo</h1>
        <p className="text-primary/70 mt-2 text-sm">Error UI demo placeholder.</p>
      </div>
    </div>
  );
}
