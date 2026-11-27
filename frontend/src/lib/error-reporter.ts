import { apiUrl, getPlatformToken, getToken } from "@/lib/api";

/**
 * Sends browser errors to Ordo's error tracker (spec 0004, AC-5):
 * `window.onerror`, unhandled promise rejections, and errors the router's
 * error screen catches. At most 5 reports per page load, and a report that
 * fails is never itself reported.
 */

const MAX_REPORTS = 5;
const STACK_MAX = 8000;
const MESSAGE_MAX = 2000;

let sent = 0;
let installed = false;
let host: "school" | "console" | "unknown" = "unknown";
const seen = new WeakSet<object>();

function authorization(): string | undefined {
  if (host === "console") {
    const token = getPlatformToken();
    return token ? `Bearer ${token}` : undefined;
  }
  const token = getToken();
  return token ? `Token ${token}` : undefined;
}

function describe(error: unknown): { name: string; message: string; stack: string } {
  if (error instanceof Error) {
    return { name: error.name || "Error", message: error.message, stack: error.stack ?? "" };
  }
  return { name: "Error", message: typeof error === "string" ? error : String(error), stack: "" };
}

export function reportError(error: unknown) {
  try {
    if (typeof window === "undefined" || sent >= MAX_REPORTS) return;
    if (error && typeof error === "object") {
      if (seen.has(error)) return;
      seen.add(error);
    }
    sent += 1;
    const { name, message, stack } = describe(error);
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const auth = authorization();
    if (auth) headers.Authorization = auth;
    void fetch(apiUrl("/api/telemetry/errors/"), {
      method: "POST",
      keepalive: true,
      headers,
      body: JSON.stringify({
        name: name.slice(0, 255),
        message: message.slice(0, MESSAGE_MAX),
        stack: stack.slice(0, STACK_MAX),
        // The server drops any query or hash too; nothing after "?" is sent.
        path: window.location.pathname,
        release: import.meta.env.VITE_RELEASE ?? "dev",
      }),
    }).catch(() => {
      // Never report a failed report.
    });
  } catch {
    // Reporting must never break the page.
  }
}

/** Listen for uncaught errors. Safe to call more than once. */
export function installErrorReporter(kind: "school" | "console" | "unknown") {
  host = kind;
  if (installed || typeof window === "undefined") return;
  installed = true;
  window.addEventListener("error", (event) => {
    // Without an error object it's a failed resource load or an opaque
    // cross origin "Script error.", with nothing to act on.
    if (event.error) reportError(event.error);
  });
  window.addEventListener("unhandledrejection", (event) => {
    reportError(event.reason);
  });
}
