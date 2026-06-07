import { Link } from "react-router-dom";
import { ArrowUpRight, ArrowRight } from "lucide-react";
import { useFeatures } from "@/api/public";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ThemeToggle } from "@/components/theme-toggle";
import { Logo } from "@/components/logo";
import { InstitutionLogo } from "@/components/institution-logo";
import { useReveal } from "@/lib/use-reveal";

function PublicHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-[color:var(--border)] bg-background/70 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6 sm:px-8">
        <Link
          to="/"
          className="flex items-center gap-2 font-serif text-[1.25rem] tracking-tight"
        >
          <Logo size={20} />
          AuraSchedule
          <InstitutionLogo size={28} className="ml-1.5" />
        </Link>
        <nav className="hidden items-center gap-7 text-[13px] text-muted-foreground md:flex">
          <Link
            to="/"
            className="transition-colors hover:text-[color:var(--brand-strong)]"
          >
            Home
          </Link>
          <Link
            to="/features"
            className="text-foreground"
            style={{ color: "var(--brand-strong)" }}
          >
            Modules
          </Link>
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle size="sm" iconOnly />
          <Button render={<Link to="/login" />} variant="brand" size="sm">
            Sign in
            <ArrowUpRight className="ml-1 size-3.5" strokeWidth={2.25} />
          </Button>
        </div>
      </div>
    </header>
  );
}

function PublicFooter() {
  return (
    <footer className="border-t border-[color:var(--border)] bg-background">
      <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-4 px-6 py-8 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground sm:flex-row sm:items-center sm:px-8">
        <span>&copy; {new Date().getFullYear()} AuraSchedule · All rights reserved.</span>
        <span className="flex items-center gap-6">
          <Link
            to="/"
            className="transition-colors hover:text-[color:var(--brand-strong)]"
          >
            Home
          </Link>
          <Link
            to="/features"
            className="transition-colors hover:text-[color:var(--brand-strong)]"
          >
            Modules
          </Link>
          <Link
            to="/login"
            className="transition-colors hover:text-[color:var(--brand-strong)]"
          >
            Sign in
          </Link>
        </span>
      </div>
    </footer>
  );
}

export default function FeaturesPage() {
  useReveal();
  const features = useFeatures();
  return (
    <div className="min-h-screen bg-background text-foreground antialiased">
      <PublicHeader />

      <main>
        {/* HERO */}
        <section className="border-b border-[color:var(--border)]">
          <div className="mx-auto max-w-7xl px-6 py-20 sm:px-8 lg:py-28">
            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 lg:col-span-7">
                <span
                  data-reveal
                  className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.18em]"
                  style={{
                    backgroundColor: "var(--brand-soft)",
                    color: "var(--brand-strong)",
                  }}
                >
                  <span
                    aria-hidden
                    className="size-1 rounded-full animate-pulse-soft"
                    style={{ backgroundColor: "var(--brand-strong)" }}
                  />
                  Index — Modules
                </span>
                <h1
                  data-reveal
                  style={{ ["--reveal-delay" as string]: "120ms" }}
                  className="mt-4 font-serif text-[3rem] leading-[1.02] tracking-[-0.02em] sm:text-[4rem] lg:text-[4.75rem]"
                >
                  Every module
                  <br />
                  the platform{" "}
                  <span
                    className="italic"
                    style={{ color: "var(--brand-strong)" }}
                  >
                    ships
                  </span>{" "}
                  with.
                </h1>
              </div>
              <div className="col-span-12 lg:col-span-5 lg:pl-8">
                <p
                  data-reveal
                  style={{ ["--reveal-delay" as string]: "240ms" }}
                  className="text-[15px] leading-[1.7] text-muted-foreground"
                >
                  AuraSchedule is a deliberately small surface — five modules, one
                  pipeline, one source of truth. Each module owns one job and
                  emits its progress over a typed event stream so the rest of
                  the system never has to guess.
                </p>
                <div
                  data-reveal
                  style={{ ["--reveal-delay" as string]: "320ms" }}
                  className="mt-6 flex items-center gap-4"
                >
                  <Button
                    render={<Link to="/login" />}
                    variant="brand"
                    size="lg"
                    className="h-11"
                  >
                    Open the dashboard
                    <ArrowRight className="ml-1.5 size-4" strokeWidth={2.25} />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* INDEX LIST */}
        <section
          className="relative"
          style={{ backgroundColor: "var(--brand-soft)" }}
        >
          <div className="mx-auto max-w-7xl px-6 py-16 sm:px-8 lg:py-24">
            <div data-reveal className="mb-10 flex items-end justify-end">
              <p className="hidden font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground sm:block">
                {features.data?.length ?? 0} modules
              </p>
            </div>

            {features.isLoading ? (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-44 rounded-[12px]" />
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {features.data?.map((f, i) => (
                  <Link
                    key={f.slug}
                    to={`/features/${f.slug}`}
                    data-reveal
                    style={
                      {
                        "--reveal-delay": `${i * 70}ms`,
                      } as React.CSSProperties
                    }
                    className="group relative flex flex-col justify-between gap-6 overflow-hidden rounded-[14px] border border-[color:var(--border)] bg-card p-7 transition-all duration-300 hover:-translate-y-0.5 hover:border-[color:var(--brand)]/40 hover:shadow-[0_22px_44px_-26px_color-mix(in_oklch,var(--brand)_60%,transparent)]"
                  >
                    {/* Top rail — slides in on hover */}
                    <span
                      aria-hidden
                      className="absolute inset-x-0 top-0 h-[3px] origin-left scale-x-0 transition-transform duration-500 ease-out group-hover:scale-x-100"
                      style={{ backgroundColor: "var(--brand)" }}
                    />
                    <div className="flex items-start justify-between gap-4">
                      <span
                        className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em]"
                        style={{
                          backgroundColor: "var(--brand-soft)",
                          color: "var(--brand-strong)",
                        }}
                      >
                        <span
                          aria-hidden
                          className="size-1 rounded-full"
                          style={{ backgroundColor: "var(--brand-strong)" }}
                        />
                        Module · {String(i + 1).padStart(2, "0")}
                      </span>
                      <ArrowUpRight
                        className="size-4 text-muted-foreground transition-all duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-[color:var(--brand-strong)]"
                        strokeWidth={2.25}
                      />
                    </div>
                    <div>
                      <h3 className="font-serif text-[1.625rem] leading-[1.1] tracking-[-0.01em]">
                        {f.title}
                      </h3>
                      <p className="mt-2 text-[14px] leading-[1.6] text-muted-foreground">
                        {f.subtitle}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* CTA — solid purple slab */}
        <section
          className="border-t border-[color:var(--border)]"
          style={{
            backgroundColor: "var(--brand)",
            color: "var(--brand-foreground)",
          }}
        >
          <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-8 px-6 py-16 sm:flex-row sm:items-center sm:px-8 lg:py-20">
            <div data-reveal>
              <p
                className="font-mono text-[10px] uppercase tracking-[0.18em]"
                style={{
                  color:
                    "color-mix(in oklch, var(--brand-foreground) 65%, transparent)",
                }}
              >
                Ready when you are
              </p>
              <h2 className="mt-3 max-w-2xl font-serif text-[2.25rem] leading-[1.05] tracking-[-0.015em] sm:text-[2.75rem]">
                Open the dashboard
                <span
                  className="italic"
                  style={{
                    color:
                      "color-mix(in oklch, var(--brand-foreground) 80%, transparent)",
                  }}
                >
                  {" "}
                  and start a session.
                </span>
              </h2>
            </div>
            <Button
              render={<Link to="/login" />}
              size="lg"
              data-reveal
              style={{ ["--reveal-delay" as string]: "120ms" }}
              className="h-11 rounded-md bg-card px-6 text-[14px] text-foreground hover:bg-background/90"
            >
              Sign in
              <ArrowRight className="ml-1.5 size-4" strokeWidth={2.25} />
            </Button>
          </div>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}
