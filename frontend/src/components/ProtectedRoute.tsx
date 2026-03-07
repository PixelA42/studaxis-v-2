/**
 * ProtectedRoute — guards routes that require authentication.
 * Shows loading spinner while auth state is resolving; redirects to /auth/login if not authenticated.
 * requireProfile=true (default): also redirects to /onboarding if profile_name is missing.
 * requireProfile=false: only checks isAuthenticated (e.g. for /onboarding route).
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

  if (!isAuthenticated) {
    return <Navigate to="/auth/login" replace state={{ from: location }} />;
  }

  if (requireProfile && !profile.profile_name) {
    return <Navigate to="/onboarding" replace />;
  }

  return <Outlet />;
}
