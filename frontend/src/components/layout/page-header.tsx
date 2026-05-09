import type { ReactNode } from "react";

type Tone = "iris" | "amber" | "coral" | "teal" | "lime" | "plum";

interface Props {
  section: string;
  title: string;
  description?: string;
  meta?: ReactNode;
  actions?: ReactNode;
  /** Color tone for the section chip. Defaults to iris (brand). */
  tone?: Tone;
  /** Reserved — currently only "editorial" is rendered. */
  variant?: "editorial";
}

export function PageHeader({
  section,
  title,
  description,
  meta,
  actions,
  tone = "iris",
}: Props) {
  return (
    <header className="flex flex-col gap-6 border-b border-[color:var(--border)] pb-8 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <span
          className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.18em]"
          style={{
            backgroundColor: `var(--accent-${tone})`,
            color: `var(--accent-${tone}-fg)`,
          }}
        >
          <span
            aria-hidden
            className="size-1 rounded-full"
            style={{ backgroundColor: `var(--accent-${tone}-fg)` }}
          />
          {section}
        </span>
        <h1 className="mt-4 font-serif text-[2.5rem] leading-[1.02] tracking-[-0.02em] text-balance sm:text-[3rem]">
          {title}
        </h1>
        {description && (
          <p className="mt-3 max-w-2xl text-[14.5px] leading-[1.65] text-muted-foreground">
            {description}
          </p>
        )}
        {meta && <div className="mt-4">{meta}</div>}
      </div>
      {actions && (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {actions}
        </div>
      )}
    </header>
  );
}
