import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  clearPlatformToken,
  getPlatformToken,
  platformApi,
  setPlatformToken,
} from "./api";

/** Owner can do everything; Support looks after schools (spec 0003, child 0003). */
export type PlatformRole = "owner" | "support";

export const PLATFORM_ROLE_LABELS: Record<PlatformRole, string> = {
  owner: "Owner",
  support: "Support",
};

export interface PlatformAdmin {
  id: number;
  email: string;
  name: string;
  role: PlatformRole;
}

export const isPlatformOwner = (a: PlatformAdmin | null) => a?.role === "owner";

/** What the password step says comes next. */
export type SignInStep =
  | { step: "totp"; challenge: string }
  | { step: "enroll"; challenge: string; otpauth_uri: string };

type Status = "loading" | "authenticated" | "unauthenticated";

interface PlatformAuthValue {
  status: Status;
  admin: PlatformAdmin | null;
  /** Password step. Resolves to the second step to show. */
  checkPassword: (email: string, password: string) => Promise<SignInStep>;
  /** Code step (`totp`) or first time authenticator setup (`enroll`). */
  confirmCode: (step: SignInStep, code: string) => Promise<PlatformAdmin>;
  logout: () => Promise<void>;
}

const PlatformAuthContext = createContext<PlatformAuthValue | undefined>(
  undefined,
);

export function PlatformAuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [admin, setAdmin] = useState<PlatformAdmin | null>(null);

  useEffect(() => {
    if (!getPlatformToken()) {
      setStatus("unauthenticated");
      return;
    }
    platformApi
      .get<PlatformAdmin>("/me/")
      .then((res) => {
        setAdmin(res.data);
        setStatus("authenticated");
      })
      .catch(() => {
        clearPlatformToken();
        setStatus("unauthenticated");
      });
  }, []);

  const checkPassword = async (email: string, password: string) => {
    const res = await platformApi.post<SignInStep>("/auth/login/", {
      email,
      password,
    });
    return res.data;
  };

  const confirmCode = async (step: SignInStep, code: string) => {
    const res = await platformApi.post<{ token: string; admin: PlatformAdmin }>(
      step.step === "enroll" ? "/auth/enroll/" : "/auth/totp/",
      { challenge: step.challenge, code },
    );
    setPlatformToken(res.data.token);
    setAdmin(res.data.admin);
    setStatus("authenticated");
    return res.data.admin;
  };

  const logout = async () => {
    try {
      await platformApi.post("/auth/logout/");
    } catch {
      // The token is wiped locally either way.
    }
    clearPlatformToken();
    setAdmin(null);
    setStatus("unauthenticated");
  };

  return (
    <PlatformAuthContext.Provider
      value={{ status, admin, checkPassword, confirmCode, logout }}
    >
      {children}
    </PlatformAuthContext.Provider>
  );
}

export function usePlatformAuth(): PlatformAuthValue {
  const ctx = useContext(PlatformAuthContext);
  if (!ctx) {
    throw new Error("usePlatformAuth must be used inside <PlatformAuthProvider>");
  }
  return ctx;
}
