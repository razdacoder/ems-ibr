import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";

interface Props {
  /** Compact size variants — match neighbouring controls. */
  size?: "sm" | "md";
  /** Hide the text label even on wider layouts. */
  iconOnly?: boolean;
  className?: string;
}

export function ThemeToggle({ size = "md", iconOnly = false, className }: Props) {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";
  const Icon = isDark ? Sun : Moon;
  const label = isDark ? "Light mode" : "Dark mode";

  return (
    <button
      type="button"
      onClick={toggle}
      role="switch"
      aria-checked={isDark}
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex items-center justify-center rounded-md border border-[color:var(--border)] bg-[color:var(--card)] text-muted-foreground transition-colors hover:border-[color:var(--brand)]/30 hover:bg-[color:var(--brand-soft)] hover:text-[color:var(--brand-strong)]",
        size === "sm"
          ? iconOnly
            ? "size-7"
            : "h-7 gap-1.5 px-2"
          : iconOnly
            ? "size-8"
            : "h-8 gap-1.5 px-2.5",
        className,
      )}
    >
      <Icon className="size-3.5" strokeWidth={2} />
      {!iconOnly && (
        <span className="font-mono text-[10px] uppercase tracking-[0.12em]">
          {isDark ? "Light" : "Dark"}
        </span>
      )}
    </button>
  );
}
