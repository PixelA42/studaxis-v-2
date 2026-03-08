/**
 * Page chrome — background blobs/glow and optional back button (Thermal Vitreous).
 */

import { Link } from "react-router-dom";
import { type ReactNode } from "react";

export function PageChrome({
  children,
  backTo,
  backLabel = "← Back to Dashboard",
}: {
  children: ReactNode;
  backTo?: string;
  backLabel?: string;
}) {
  return (
    <div className="relative z-10">
      <div className="ambient-glow" aria-hidden />
      {backTo && (
        <div className="mb-4">
          <Link
            to={backTo}
            className="chrome-back-btn"
            aria-label={`Back: ${backLabel.replace(/←\s*/g, "").trim()}`}
          >
            {backLabel}
          </Link>
        </div>
      )}
      {children}
    </div>
  );
}
