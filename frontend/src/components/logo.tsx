import { cn } from "@/lib/utils";

/**
 * AuraSchedule mark — concentric rings around a focal centre.
 *
 * Reads as a target / moment-with-awareness: the inner solid disc is "the
 * scheduled moment", the surrounding rings are its "aura". Pure geometric SVG
 * scaled to the host font-size by default so it sits cleanly next to a serif
 * wordmark.
 */
export function Logo({
  className,
  size = 16,
  /** When true, render only the central disc (favicon-style condensed mark). */
  condensed = false,
}: {
  className?: string;
  size?: number;
  condensed?: boolean;
}) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 24 24"
      width={size}
      height={size}
      className={cn("shrink-0", className)}
      style={{ color: "var(--brand)" }}
    >
      {!condensed && (
        <>
          {/* Outer ring — the aura */}
          <circle
            cx="12"
            cy="12"
            r="10.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            opacity="0.35"
          />
          {/* Mid ring — heavier weight, anchors the mark */}
          <circle
            cx="12"
            cy="12"
            r="6.75"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
          />
        </>
      )}
      {/* Centre disc — the moment */}
      <circle cx="12" cy="12" r="2.75" fill="currentColor" />
    </svg>
  );
}

/**
 * Wordmark + mark, the standard header brand-line. Use this anywhere the
 * literal "AuraSchedule" string appears next to the logo.
 */
export function Wordmark({
  className,
  size = "md",
}: {
  className?: string;
  size?: "sm" | "md" | "lg";
}) {
  const px = size === "lg" ? 22 : size === "sm" ? 14 : 18;
  const text =
    size === "lg"
      ? "text-[1.5rem]"
      : size === "sm"
        ? "text-[1.125rem]"
        : "text-[1.25rem]";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 font-serif tracking-tight",
        text,
        className,
      )}
    >
      <Logo size={px} />
      AuraSchedule
    </span>
  );
}
