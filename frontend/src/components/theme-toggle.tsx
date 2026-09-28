import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/lib/theme";

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
    <Button
      type="button"
      variant="outline"
      size={
        iconOnly
          ? size === "sm"
            ? "icon-sm"
            : "icon"
          : size === "sm"
            ? "sm"
            : "default"
      }
      onClick={toggle}
      role="switch"
      aria-checked={isDark}
      aria-label={label}
      title={label}
      className={className}
    >
      <Icon data-icon={iconOnly ? undefined : "inline-start"} strokeWidth={2} />
      {!iconOnly && (isDark ? "Light" : "Dark")}
    </Button>
  );
}
