import { Wordmark } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";

/*
 * Shown on a school host instead of every page while the school isn't open:
 * suspended (or pending deletion), or still being set up. The wording is
 * fixed; the reason for a suspension stays in the console.
 */

function ClosedFrame({ eyebrow, title, children }: { eyebrow: string; title: string; children: string }) {
  return (
    <main className="relative flex min-h-screen flex-col bg-background">
      <div className="flex items-center justify-between p-6">
        <Wordmark size="md" />
        <ThemeToggle size="sm" iconOnly />
      </div>

      <div className="flex flex-1 items-center justify-center px-6 pb-24">
        <div className="max-w-md text-center">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            {eyebrow}
          </p>
          <h1 className="mt-4 font-serif text-[2.25rem] leading-[1.05] tracking-[-0.02em] text-foreground text-balance">
            {title}
          </h1>
          <p className="mt-4 text-[15px] leading-[1.7] text-muted-foreground">{children}</p>
        </div>
      </div>
    </main>
  );
}

export function SchoolSuspendedPage({ name }: { name: string }) {
  return (
    <ClosedFrame eyebrow={name} title="Access is suspended">
      This school's access is suspended. Contact Ordo.
    </ClosedFrame>
  );
}

export function SchoolSettingUpPage({ name }: { name: string }) {
  return (
    <ClosedFrame eyebrow={name} title="Being set up">
      Ordo is still getting this school ready. Check back in a few minutes, or use the link in your
      invite email once it arrives.
    </ClosedFrame>
  );
}
