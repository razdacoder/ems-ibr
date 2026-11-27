import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { readStoredTheme, storeTheme, type Theme } from "./theme-cookie";

interface ThemeContext {
  theme: Theme;
  setTheme: (next: Theme) => void;
  toggle: () => void;
}

const Ctx = createContext<ThemeContext | null>(null);

function apply(theme: Theme) {
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.style.colorScheme = theme;
}

/**
 * The server can't know the visitor's theme, so the inline script in
 * __root.tsx sets it before paint and this provider reads it back after
 * hydration. Until then `theme` reports "light"; render theme-dependent UI
 * with `dark:` classes rather than from `theme` so it's right from the
 * first paint.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("light");

  useEffect(() => {
    setThemeState(
      document.documentElement.classList.contains("dark") ? "dark" : "light",
    );
  }, []);

  // Follow OS changes only when the user has not made an explicit choice.
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (e: MediaQueryListEvent) => {
      if (readStoredTheme()) return;
      const next = e.matches ? "dark" : "light";
      apply(next);
      setThemeState(next);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const setTheme = useCallback((next: Theme) => {
    apply(next);
    storeTheme(next);
    setThemeState(next);
  }, []);
  const toggle = useCallback(
    () => setTheme(document.documentElement.classList.contains("dark") ? "light" : "dark"),
    [setTheme],
  );

  return <Ctx.Provider value={{ theme, setTheme, toggle }}>{children}</Ctx.Provider>;
}

export function useTheme(): ThemeContext {
  const v = useContext(Ctx);
  if (!v) throw new Error("useTheme must be used inside <ThemeProvider>");
  return v;
}
