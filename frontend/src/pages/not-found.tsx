import { ArrowRight } from "lucide-react";
import { Wordmark } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { buttonVariants } from "@/components/ui/button";
import { useOrigins } from "@/lib/config";

/**
 * Shown on a host that isn't a live school (unknown or purged), and on the
 * wrong host for a route (school pages on console.<base>, console pages on a
 * school). Says the same thing every time, so it reveals nothing about which
 * schools exist.
 */
export default function NotFoundPage() {
  const { site } = useOrigins();

  return (
    <main className="relative flex min-h-screen flex-col bg-background">
      <div className="flex items-center justify-between p-6">
        {site ? (
          <a href={`${site}/`} className="inline-flex">
            <Wordmark size="md" />
          </a>
        ) : (
          <Wordmark size="md" />
        )}
        <ThemeToggle size="sm" iconOnly />
      </div>

      <div className="flex flex-1 items-center justify-center px-6 pb-24">
        <div className="max-w-md text-center">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            404
          </p>
          <h1 className="mt-4 font-serif text-[2.25rem] leading-[1.05] tracking-[-0.02em] text-foreground text-balance">
            School not found
          </h1>
          <p className="mt-4 text-[15px] leading-[1.7] text-muted-foreground">
            There's no Ordo school at this address. Check the link you were
            given, or ask your exams office for the right one.
          </p>
          {site && (
            <a
              href={`${site}/`}
              className={buttonVariants({ variant: "outline", className: "mt-8" })}
            >
              Go to the Ordo website
              <ArrowRight aria-hidden />
            </a>
          )}
        </div>
      </div>
    </main>
  );
}
