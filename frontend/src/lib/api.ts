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
