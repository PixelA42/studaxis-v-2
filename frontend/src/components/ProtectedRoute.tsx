/**
 * ProtectedRoute — guards routes that require authentication.
 * Shows loading spinner while auth state is resolving; redirects to /auth/login if not authenticated.
 * requireProfile=true (default): also redirects to /onboarding if profile_name is missing.
 * requireProfile=false: ONLY checks isAuthenticated (e.g. for /onboarding route).
 *   - if !isAuthenticated → /login
 *   - if isAuthenticated  → Outlet (no profile_name check, no onboarding_complete check)
 */

import { Outlet, useLocation } from "react-router-dom";
import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { LoadingSpinner } from "./LoadingSpinner";

export function ProtectedRoute({ requireProfile = true }: { requireProfile?: boolean }) {
  const { isAuthenticated, isLoading, profile } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-[40vh] flex items-center justify-center">
        <LoadingSpinner message="Loading…" />
      </div>
    );
  }

  // /onboarding and any other requireProfile=false routes:
  // Only gate on isAuthenticated. Do NOT check profile_name or onboarding_complete —
  // those are exactly the fields that haven't been set yet right after OTP verification.
  if (requireProfile === false) {
    if (!isAuthenticated) {
      return <Navigate to="/login" replace />;
    }
    return <Outlet />;
  }

  // Default (requireProfile=true): full guard for authenticated + profiled users.
  if (!isAuthenticated) {
    return <Navigate to="/auth/login" replace state={{ from: location }} />;
  }

  if (!profile.profile_name) {
    return <Navigate to="/onboarding" replace />;
  }

  return <Outlet />;
}
