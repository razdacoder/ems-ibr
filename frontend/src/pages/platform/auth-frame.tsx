import type { ReactNode } from "react";
import { Wordmark } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";

/** Single column frame for the console's sign in and invite pages. */
export function ConsoleAuthFrame({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description?: ReactNode;
  children: ReactNode;
}) {
  return (
    <main className="flex min-h-screen flex-col bg-background">
      <div className="flex items-center justify-between border-b border-[color:var(--border)] px-6 py-5">
        <span className="inline-flex items-center gap-3">
          <Wordmark />
          <span className="rounded-full border border-[color:var(--border)] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            Console
          </span>
        </span>
        <ThemeToggle size="sm" iconOnly />
      </div>
      <div className="flex flex-1 items-center justify-center px-4 py-16 sm:px-6">
        <div className="w-full max-w-[400px]">
          <span
            className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.18em]"
            style={{
              backgroundColor: "var(--brand-soft)",
              color: "var(--brand-strong)",
            }}
          >
            {eyebrow}
          </span>
          <h1 className="mt-4 font-serif text-[2.25rem] leading-[1.05] tracking-[-0.02em]">
            {title}
          </h1>
          {description && (
            <div className="mt-3 text-[14.5px] leading-[1.65] text-muted-foreground">
              {description}
            </div>
          )}
          <div className="mt-8">{children}</div>
        </div>
      </div>
    </main>
  );
}
