/**
 * The theme preference lives in a cookie on the parent domain (ordo.app),
 * so the site and the dashboard (app.ordo.app) share it — localStorage is
 * per-origin and would keep a separate setting on each host. On bare
 * `localhost` browsers refuse a Domain cookie, so it's host-only there; use
 * ordo.localhost / app.ordo.localhost in dev to share it.
 *
 * THEME_SCRIPT in routes/__root.tsx repeats this logic inline (it runs
 * before any module loads) — keep the two in sync.
 */

export type Theme = "light" | "dark";

export const THEME_COOKIE = "ordo-theme";
/** Where older builds kept the preference; read once as a fallback. */
const LEGACY_KEY = "ordo:theme";

function cookieDomain(): string | null {
  const host = window.location.hostname.replace(/^(app|www)\./, "");
  return host.includes(".") ? host : null;
}

export function readStoredTheme(): Theme | null {
  const match = document.cookie.match(/(?:^|;\s*)ordo-theme=(light|dark)/);
  if (match) return match[1] as Theme;
  try {
    const legacy = localStorage.getItem(LEGACY_KEY);
    if (legacy === "light" || legacy === "dark") return legacy;
  } catch {
    // storage blocked — fall through to the OS preference
  }
  return null;
}

export function storeTheme(theme: Theme) {
  const domain = cookieDomain();
  document.cookie =
    `${THEME_COOKIE}=${theme}; Path=/; Max-Age=31536000; SameSite=Lax` +
    (domain ? `; Domain=${domain}` : "");
}
