import type { ReactNode } from "react";

interface Props {
  section: string;
  title: string;
  description?: string;
  meta?: ReactNode;
  actions?: ReactNode;
  /** Reserved — currently only "editorial" is rendered. */
  variant?: "editorial";
}

export function PageHeader({
  section,
  title,
  description,
  meta,
  actions,
}: Props) {
  return (
    <header className="flex flex-col gap-6 border-b border-[color:var(--border)] pb-8 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          § {section}
        </p>
        <h1 className="mt-3 font-serif text-[2.5rem] leading-[1.05] tracking-[-0.015em] sm:text-[3rem]">
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
