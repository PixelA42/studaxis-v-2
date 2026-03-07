export interface HardwareStatusProps {
  /** Local AI model name (e.g. from Ollama / AIConfig) */
  modelName?: string | null;
  /** RAM used in GB (e.g. from psutil) */
  ramUsedGb?: number | null;
  /** Total RAM in GB */
  ramTotalGb?: number | null;
  /** Status for styling: warn = low power / low RAM */
  status?: "ok" | "warn" | "error";
  /** When true, show the low-power pill (replaces render_low_power_indicator) */
  lowPowerMode?: boolean;
  className?: string;
}

/**
 * Displays local model and RAM usage — Thermal Vitreous.
 * Replaces Streamlit hardware/performance indicators. Data typically from backend /api/health or /api/hardware.
 */
export function HardwareStatus({
  modelName,
  ramUsedGb,
  ramTotalGb,
  status = "ok",
  lowPowerMode = false,
  className = "",
}: HardwareStatusProps) {
  const ramText =
    ramUsedGb != null && ramTotalGb != null
      ? `${ramUsedGb.toFixed(1)} / ${ramTotalGb.toFixed(1)} GB`
      : "—";

  const statusStyles = {
    ok: "border-glass-border text-primary/80",
    warn: "border-amber-500/40 text-amber-400/90 bg-amber-500/10",
    error: "border-red-500/40 text-red-400/90 bg-red-500/10",
  };

  return (
    <div className={`flex flex-wrap items-center gap-3 ${className}`}>
      {/* Model + RAM pill */}
      <div
        className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium ${statusStyles[status]}`}
        role="status"
        aria-label={`Local model: ${modelName ?? "unknown"}. RAM: ${ramText}`}
      >
        <span className="font-mono text-primary/70">Model</span>
        <span className="font-mono text-primary">
          {modelName ?? "—"}
        </span>
        <span className="text-glass-border">·</span>
        <span className="font-mono text-primary/70">RAM</span>
        <span className="font-mono text-primary">{ramText}</span>
      </div>

      {/* Low power mode pill (matches performance_ui.render_low_power_indicator) */}
      {lowPowerMode && (
        <span
          className="inline-flex items-center gap-1.5 rounded-full border border-glass-border bg-surface-light px-3 py-1.5 text-xs font-semibold text-primary/70"
          role="status"
          aria-label="Low Power Mode Active"
        >
          <span
            className="h-1.5 w-1.5 rounded-full bg-primary/50"
            aria-hidden
          />
          Low Power Mode — Reduced animations
        </span>
      )}
    </div>
  );
}
