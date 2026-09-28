import { InstitutionLogo } from "@/components/institution-logo";
import { cn } from "@/lib/utils";

/**
 * Ordo mark — a square "O" with its top-right corner lifted out as a single
 * Signal-green seat. Reads as the O of Ordo and as a seat being placed: the
 * product's job in one glyph. Drawn on a 24-unit grid so every edge lands on
 * a whole pixel at 16/24/32px.
 */
export function Logo({
  className,
  size = 16,
}: {
  className?: string;
  size?: number;
}) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 24 24"
      width={size}
      height={size}
      className={cn("shrink-0", className)}
      shapeRendering="crispEdges"
    >
      <path
        d="M1 1H13V6H6V18H18V11H23V23H1Z"
        fill="currentColor"
      />
      <rect x="15" y="1" width="8" height="8" fill="var(--brand)" />
    </svg>
  );
}

const WORDMARK_SIZES = {
  sm: { mark: 16, text: "text-[1rem]" },
  md: { mark: 18, text: "text-[1.125rem]" },
  lg: { mark: 22, text: "text-[1.375rem]" },
} as const;

/**
 * Mark + "Ordo" set in the heading face. Use this anywhere the literal
 * "Ordo" string appears next to the logo.
 */
export function Wordmark({
  className,
  size = "md",
}: {
  className?: string;
  size?: keyof typeof WORDMARK_SIZES;
}) {
  const s = WORDMARK_SIZES[size];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 font-heading font-semibold leading-none tracking-[-0.03em]",
        s.text,
        className,
      )}
    >
      <Logo size={s.mark} />
      Ordo
    </span>
  );
}

/**
 * Ordo wordmark co-branded with the configured institution logo, separated
 * by a hairline rule. Falls back to the bare wordmark when no institution
 * logo has been uploaded.
 */
export function BrandLockup({
  className,
  size = "md",
}: {
  className?: string;
  size?: keyof typeof WORDMARK_SIZES;
}) {
  return (
    <span className={cn("inline-flex items-center gap-3", className)}>
      <Wordmark size={size} />
      <InstitutionLogo size={size === "lg" ? 32 : 28} withDivider />
    </span>
  );
}
