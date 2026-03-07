/**
 * Status indicator — sync/connectivity pill (Online / Offline).
 */

export function StatusIndicator({
  status,
  label,
}: {
  status: "online" | "offline" | "unknown";
  label?: string;
}) {
  const isOnline = status === "online";
  const text =
    label ??
    (status === "online"
      ? "● Online"
      : status === "offline"
        ? "○ Offline — Studaxis works fully offline"
        : "Detecting...");

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium ${
        isOnline
          ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10"
          : "border-glass-border text-primary/70 bg-surface-light"
      }`}
      role="status"
      aria-label={text}
    >
      {text}
    </span>
  );
}
