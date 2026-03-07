/**
 * Auth context — JWT-based authentication state.
 * Token stored in localStorage; isAuthenticated derived from token presence.
 * Refresh maintains logged-in state if token exists.
 */

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
} from "../services/api";

const STORAGE_KEY = "studaxis_profile";
const STORAGE_TOKEN = "studaxis_token";

export interface Profile {
  profile_name: string | null;
  profile_mode: "solo" | "teacher_linked" | "teacher_linked_provisional" | null;
  class_code: string | null;
  user_role: "student" | "teacher" | null;
}

const defaultProfile: Profile = {
  profile_name: null,
  profile_mode: null,
  class_code: null,
  user_role: null,
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
      };
    }
  } catch {
    // ignore
  }
  return defaultProfile;
}

/** Token presence = authenticated; refresh maintains state if token exists */
function loadLoggedIn(): boolean {
  return !!localStorage.getItem(STORAGE_TOKEN);
}

interface AuthContextValue {
  isAuthenticated: boolean;
  userLoggedIn: boolean; // alias for isAuthenticated (backward compat)
  profile: Profile;
  setProfile: (p: Partial<Profile>) => void;
  login: (usernameOrEmail: string, password: string) => Promise<void>;
  signup: (auth: AuthResponse) => void;
  logout: () => void;
  connectivityStatus: "online" | "offline" | "unknown";
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [userLoggedIn, setUserLoggedIn] = useState(loadLoggedIn);
  const [profile, setProfileState] = useState<Profile>(loadStoredProfile);
  const [connectivityStatus, setConnectivityStatus] = useState<
    "online" | "offline" | "unknown"
  >("unknown");

  useEffect(() => {
    getHealth()
      .then(() => setConnectivityStatus("online"))
      .catch(() => setConnectivityStatus("offline"));
  }, []);

  useEffect(() => {
    if (connectivityStatus !== "online") return;
    getUserProfile()
      .then((backend) => {
        const merged = {
          profile_name: backend.profile_name ?? null,
          profile_mode: backend.profile_mode ?? null,
          class_code: backend.class_code ?? null,
          user_role: backend.user_role ?? null,
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

  const setProfile = useCallback((p: Partial<Profile>) => {
    setProfileState((prev) => {
      const next = { ...prev, ...p };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // ignore
      }
      if (connectivityStatus === "online") {
        postUserProfile(next).catch(() => {
          // Offline or error; localStorage already updated
        });
      }
      return next;
    });
  }, [connectivityStatus]);

  const login = useCallback(
    async (usernameOrEmail: string, password: string) => {
      const auth = await postLogin({ username_or_email: usernameOrEmail, password });
      localStorage.setItem(STORAGE_TOKEN, auth.access_token);
      setProfileState((prev) => {
        const next = { ...prev, profile_name: auth.username };
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        } catch {
          // ignore
        }
        return next;
      });
      setUserLoggedIn(true);
    },
    []
  );

  const signup = useCallback((auth: AuthResponse) => {
    localStorage.setItem(STORAGE_TOKEN, auth.access_token);
    setProfileState((prev) => {
      const next = { ...prev, profile_name: auth.username };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // ignore
      }
      return next;
    });
    setUserLoggedIn(true);
  }, []);

  const logout = useCallback(() => {
    setUserLoggedIn(false);
    setProfileState(defaultProfile);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(STORAGE_TOKEN);
    navigate("/auth", { replace: true });
  }, [navigate]);

  const value = useMemo(
    () => ({
      isAuthenticated: userLoggedIn,
      userLoggedIn,
      profile,
      setProfile,
      login,
      signup,
      logout,
      connectivityStatus,
    }),
    [userLoggedIn, profile, setProfile, login, signup, logout, connectivityStatus]
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
