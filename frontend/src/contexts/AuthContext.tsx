/**
 * Auth context — JWT-based authentication state.
 * Token stored in localStorage; user decoded from JWT; isAuthenticated derived from valid token.
 * On load: checks token, decodes, validates expiry; if expired → logout.
 */

import { jwtDecode } from "jwt-decode";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import type { AuthResponse } from "../services/api";
import {
  getHealth,
  getUserProfile,
  postLogin,
  postUserProfile,
  setUnauthorizedHandler,
} from "../services/api";

const STORAGE_KEY = "studaxis_profile";
const STORAGE_TOKEN = "studaxis_token";

/** Decoded JWT payload (backend: sub, username, exp, iat) */
export interface JwtPayload {
  sub: string;
  username: string;
  exp: number;
  iat?: number;
}

/** User object derived from JWT + API response */
export interface AuthUser {
  id: string;
  username: string;
  email?: string;
}

export interface Profile {
  profile_name: string | null;
  profile_mode: "solo" | "teacher_linked" | "teacher_linked_provisional" | null;
  class_code: string | null;
  user_role: "student" | "teacher" | null;
  onboarding_complete: boolean;
}

const defaultProfile: Profile = {
  profile_name: null,
  profile_mode: null,
  class_code: null,
  user_role: null,
  onboarding_complete: false,
};

function loadStoredProfile(): Profile {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const o = JSON.parse(raw) as Partial<Profile>;
      return {
        profile_name: o.profile_name ?? null,
        profile_mode: o.profile_mode ?? null,
        class_code: o.class_code ?? null,
        user_role: o.user_role ?? null,
        onboarding_complete: o.onboarding_complete ?? false,
      };
    }
  } catch {
    // ignore
  }
  return defaultProfile;
}

function isTokenExpired(exp: number): boolean {
  // exp is seconds since epoch; add 60s buffer
  return Date.now() >= (exp - 60) * 1000;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  userLoggedIn: boolean; // alias for isAuthenticated (backward compat)
  profile: Profile;
  setProfile: (p: Partial<Profile>) => void;
  pendingOTP: boolean;
  pendingEmail: string;
  afterSignupStarted: (email: string) => void;
  afterOTPVerified: (token: string) => void;
  /** Accept JWT from backend, decode, save, update state */
  login: (token: string, userInfo?: { username?: string; email?: string }) => void;
  /** Convenience: authenticate with credentials, then call login with token */
  loginWithCredentials: (usernameOrEmail: string, password: string) => Promise<void>;
  signup: (auth: AuthResponse) => void;
  /** Optional redirectTo: defaults to /auth; use /auth/login for 401 redirect */
  logout: (redirectTo?: string) => void;
  connectivityStatus: "online" | "offline" | "unknown";
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [pendingOTP, setPendingOTP] = useState(false);
  const [pendingEmail, setPendingEmail] = useState("");
  const [profile, setProfileState] = useState<Profile>(loadStoredProfile);
  const [connectivityStatus, setConnectivityStatus] = useState<
    "online" | "offline" | "unknown"
  >("unknown");

  /** Register 401 handler: on API 401, logout and redirect to /auth/login */
  useEffect(() => {
    setUnauthorizedHandler(() => logout("/auth/login"));
    return () => setUnauthorizedHandler(null);
  }, []);

  /** On initial load: check localStorage for token; validate expiry */
  useEffect(() => {
    const tokenVersion = localStorage.getItem("studaxis_token_version");
    if (tokenVersion !== "v2") {
      localStorage.clear();
      localStorage.setItem("studaxis_token_version", "v2");
      setIsLoading(false);
      return;
    }
    const token = localStorage.getItem(STORAGE_TOKEN);
    if (!token) {
      setIsLoading(false);
      return;
    }
    try {
      const decoded = jwtDecode<JwtPayload>(token);
      if (isTokenExpired(decoded.exp)) {
        localStorage.removeItem(STORAGE_TOKEN);
        setUser(null);
      } else {
        setUser({
          id: decoded.sub,
          username: decoded.username,
        });
      }
    } catch {
      localStorage.removeItem(STORAGE_TOKEN);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /** Offline/online detection: navigator.onLine + periodic health checks */
  useEffect(() => {
    const check = () => {
      if (!navigator.onLine) {
        setConnectivityStatus("offline");
        return;
      }
      getHealth()
        .then(() => setConnectivityStatus("online"))
        .catch(() => setConnectivityStatus("offline"));
    };

    check();
    const interval = setInterval(check, 45000);
    window.addEventListener("online", check);
    window.addEventListener("offline", () => setConnectivityStatus("offline"));
    return () => {
      clearInterval(interval);
      window.removeEventListener("online", check);
      window.removeEventListener("offline", () => setConnectivityStatus("offline"));
    };
  }, []);

  useEffect(() => {
    if (connectivityStatus !== "online") return;
    if (!localStorage.getItem(STORAGE_TOKEN)) return;
    getUserProfile()
      .then((backend) => {
        const merged = {
          profile_name: backend.profile_name ?? null,
          profile_mode: backend.profile_mode ?? null,
          class_code: backend.class_code ?? null,
          user_role: backend.user_role ?? null,
          onboarding_complete: backend.onboarding_complete ?? false,
        };
        setProfileState((prev) => {
          const next = { ...prev, ...merged };
          try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
          } catch {
            // ignore
          }
          return next;
        });
      })
      .catch(() => {
        // Backend unreachable; keep localStorage
      });
  }, [connectivityStatus]);

  /** Always persist to local FastAPI backend (Edge Brain on localhost). Sync is local-first. */
  const setProfile = useCallback((p: Partial<Profile>) => {
    setProfileState((prev) => {
      const next = { ...prev, ...p };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // ignore
      }
      postUserProfile(next).catch(() => {
        // Backend unreachable; localStorage already updated
      });
      return next;
    });
  }, []);

  /** Accept JWT, decode, save to localStorage, update user state */
  const login = useCallback((token: string, userInfo?: { username?: string; email?: string }) => {
    try {
      const decoded = jwtDecode<JwtPayload>(token);
      if (isTokenExpired(decoded.exp)) {
        localStorage.removeItem(STORAGE_TOKEN);
        setUser(null);
        return;
      }
      localStorage.setItem(STORAGE_TOKEN, token);
      setUser({
        id: decoded.sub,
        username: userInfo?.username ?? decoded.username,
        email: userInfo?.email,
      });
      setProfileState((prev) => {
        const next = { ...prev, profile_name: userInfo?.username ?? decoded.username };
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        } catch {
          // ignore
        }
        return next;
      });
    } catch {
      localStorage.removeItem(STORAGE_TOKEN);
      setUser(null);
    }
  }, []);

  const logout = useCallback((redirectTo = "/auth") => {
    setUser(null);
    setProfileState(defaultProfile);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(STORAGE_TOKEN);
    navigate(redirectTo, { replace: true });
  }, [navigate]);

  /** Register 401 handler: on backend 401, logout and redirect to login page */
  useEffect(() => {
    setUnauthorizedHandler(() => logout("/auth/login"));
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  /** Convenience: call API, then login with token. Sets onboarding_complete from response. */
  const loginWithCredentials = useCallback(
    async (usernameOrEmail: string, password: string) => {
      const auth = await postLogin({ username_or_email: usernameOrEmail, password });
      login(auth.access_token, { username: auth.username, email: auth.email });
      setProfileState((prev) => {
        const next = { ...prev, onboarding_complete: auth.onboarding_complete ?? false };
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        } catch {
          // ignore
        }
        return next;
      });
    },
    [login]
  );

  const signup = useCallback(
    (auth: AuthResponse) => {
      login(auth.access_token, { username: auth.username, email: auth.email });
      setProfileState((prev) => {
        const next = { ...prev, onboarding_complete: auth.onboarding_complete ?? false };
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        } catch {
          // ignore
        }
        return next;
      });
    },
    [login]
  );

  const afterSignupStarted = useCallback((email: string) => {
    setPendingOTP(true);
    setPendingEmail(email);
    // do NOT set isAuthenticated here
  }, []);

  const afterOTPVerified = useCallback(
    (token: string) => {
      setPendingOTP(false);
      setPendingEmail("");
      login(token);
    },
    [login]
  );

  const isAuthenticated = user !== null;

  const value = useMemo(
    () => ({
      user,
      isAuthenticated,
      isLoading,
      userLoggedIn: isAuthenticated,
      profile,
      setProfile,
      pendingOTP,
      pendingEmail,
      afterSignupStarted,
      afterOTPVerified,
      login,
      loginWithCredentials,
      signup,
      logout,
      connectivityStatus,
    }),
    [
      user,
      isAuthenticated,
      isLoading,
      profile,
      setProfile,
      pendingOTP,
      pendingEmail,
      afterSignupStarted,
      afterOTPVerified,
      login,
      loginWithCredentials,
      signup,
      logout,
      connectivityStatus,
    ]
  );

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
