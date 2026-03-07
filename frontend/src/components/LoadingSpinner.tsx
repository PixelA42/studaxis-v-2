import { type ReactNode } from "react";

export interface LoadingSpinnerProps {
  /** Optional message shown next to the spinner (e.g. "Generating...") */
  message?: string;
  /** Optional: when true, show spinner + message; when false, render children. Replaces Streamlit's with st.spinner(): block. */
  loading?: boolean;
  children?: ReactNode;
  className?: string;
}

/**
 * Loading spinner — Thermal Vitreous. Replaces Streamlit's st.spinner.
 * Use as inline spinner with optional message, or as wrapper: loading ? spinner : children.
 */
export function LoadingSpinner({
  message,
  loading = true,
  children,
  className = "",
}: LoadingSpinnerProps) {
  const spinner = (
    <div
      className={`flex items-center gap-3 ${className}`}
      role="status"
      aria-live="polite"
      aria-label={message ?? "Loading"}
    >
      <div className="loading-spinner" aria-hidden />
      {message && (
        <span className="text-sm text-primary/80 font-medium">{message}</span>
      )}
    </div>
  );

  if (children !== undefined) {
    return loading ? spinner : <>{children}</>;
  }
  return spinner;
}
