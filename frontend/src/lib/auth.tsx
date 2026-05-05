import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api, clearToken, getToken, setToken } from "./api";

export interface AuthUser {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  is_staff: boolean;
  is_active: boolean;
  department: { id: number; name: string; slug: string } | null;
}

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setStatus("unauthenticated");
      return;
    }
    api
      .get<AuthUser>("/auth/me/")
      .then((res) => {
        setUser(res.data);
        setStatus("authenticated");
      })
      .catch(() => {
        clearToken();
        setUser(null);
        setStatus("unauthenticated");
      });
  }, []);

  const login = async (email: string, password: string) => {
    const res = await api.post<{ token: string; user: AuthUser }>(
      "/auth/login/",
      { email, password },
    );
    setToken(res.data.token);
    setUser(res.data.user);
    setStatus("authenticated");
    return res.data.user;
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout/");
    } catch {
      // Ignore network errors on logout — token is wiped locally anyway.
    }
    clearToken();
    setUser(null);
    setStatus("unauthenticated");
  };

  return (
    <AuthContext.Provider value={{ status, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
