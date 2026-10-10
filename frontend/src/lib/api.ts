import axios, { AxiosError } from "axios";

const TOKEN_KEY = "ems.token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// Django answers on the page's own origin (Traefik routes /api and /ws to it).
// The server works it out per request and the root route hands it over here
// before any page renders.
let apiOrigin = "";

export function setApiOrigin(origin: string) {
  apiOrigin = origin;
  api.defaults.baseURL = `${origin}/api`;
  platformApi.defaults.baseURL = `${origin}/api/platform`;
}

/** WebSocket URL on the Django origin, e.g. wsUrl("/ws/notifications/"). */
export function wsUrl(path: string): string {
  return (apiOrigin || window.location.origin).replace(/^http/, "ws") + path;
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      clearToken();
      if (!window.location.pathname.startsWith("/login")) {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  },
);

/*
 * The platform console (admin.<base>) has its own token, kept apart from the
 * school one, sent as a Bearer token. Django never accepts either on the
 * other's host.
 */
const PLATFORM_TOKEN_KEY = "ordo.platform.token";

export function getPlatformToken(): string | null {
  return localStorage.getItem(PLATFORM_TOKEN_KEY);
}

export function setPlatformToken(token: string) {
  localStorage.setItem(PLATFORM_TOKEN_KEY, token);
}

export function clearPlatformToken() {
  localStorage.removeItem(PLATFORM_TOKEN_KEY);
}

export const platformApi = axios.create({
  baseURL: "/api/platform",
  headers: { "Content-Type": "application/json" },
});

platformApi.interceptors.request.use((config) => {
  const token = getPlatformToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

platformApi.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Expired or revoked session. Sign in steps answer 400/410/429, not 401.
    if (error.response?.status === 401 && getPlatformToken()) {
      clearPlatformToken();
      window.location.assign("/console/login");
    }
    return Promise.reject(error);
  },
);

export interface ApiErrorEnvelope {
  detail: string;
  errors?: Record<string, string[]>;
}

export function extractErrorEnvelope(error: unknown): ApiErrorEnvelope {
  if (error instanceof AxiosError && error.response?.data) {
    const data = error.response.data as Partial<ApiErrorEnvelope>;
    if (data.detail) {
      return { detail: data.detail, errors: data.errors };
    }
  }
  return { detail: "Something went wrong. Please try again." };
}
