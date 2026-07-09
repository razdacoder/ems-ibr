import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowUpRight, ArrowRight, Check } from "lucide-react";
import { useFeature } from "@/api/public";
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
          Ordo
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
            className="transition-colors hover:text-[color:var(--brand-strong)]"
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

function Section({
  num,
  label,
  title,
  children,
}: {
  num: string;
  label: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-[color:var(--border)]">
      <div className="mx-auto grid max-w-7xl grid-cols-12 gap-6 px-6 py-16 sm:px-8 lg:py-24">
        <div className="col-span-12 lg:col-span-4" data-reveal>
          <div className="flex items-center gap-2">
            <span
              aria-hidden
              className="size-1.5 rounded-full animate-pulse-soft"
              style={{ backgroundColor: "var(--brand)" }}
            />
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
              {num} — {label}
            </p>
          </div>
          <h2 className="mt-3 font-serif text-[2rem] leading-[1.05] tracking-[-0.015em] sm:text-[2.5rem]">
            {title}
          </h2>
        </div>
        <div
          className="col-span-12 lg:col-span-8 lg:pl-8"
          data-reveal
          style={{ ["--reveal-delay" as string]: "120ms" }}
        >
          {children}
        </div>
      </div>
    </section>
  );
}

export default function FeatureDetailPage() {
  useReveal();
  const { slug } = useParams<{ slug: string }>();
  const feature = useFeature(slug);

  return (
    <div className="min-h-screen bg-background text-foreground antialiased">
      <PublicHeader />

      <main>
        {/* Crumb */}
        <div
          className="border-b border-[color:var(--border)]"
          style={{
            backgroundColor:
              "color-mix(in oklch, var(--brand-soft) 60%, transparent)",
          }}
        >
          <div className="mx-auto flex max-w-7xl items-center gap-4 px-6 py-4 text-[12px] text-muted-foreground sm:px-8">
            <Link
              to="/features"
              className="group inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] transition-colors hover:text-[color:var(--brand-strong)]"
            >
              <ArrowLeft
                className="size-3 transition-transform duration-300 group-hover:-translate-x-0.5"
                strokeWidth={2.25}
              />
              All modules
            </Link>
            <span aria-hidden className="text-muted-foreground/40">
              /
            </span>
            <span
              className="font-mono text-[10px] uppercase tracking-[0.14em]"
              style={{ color: "var(--brand-strong)" }}
            >
              {slug}
            </span>
          </div>
        </div>

        {feature.isLoading ? (
          <div className="mx-auto max-w-7xl px-6 py-16 sm:px-8">
            <Skeleton className="h-12 w-3/4" />
            <Skeleton className="mt-4 h-6 w-1/2" />
            <Skeleton className="mt-12 h-64 w-full" />
          </div>
        ) : feature.error ? (
          <div className="mx-auto max-w-7xl px-6 py-24 text-center sm:px-8">
            <p
              className="font-mono text-[10px] uppercase tracking-[0.16em]"
              style={{ color: "var(--brand-strong)" }}
            >
              404 · Not found
            </p>
            <h1 className="mt-4 font-serif text-[2.5rem] tracking-[-0.015em]">
              That module could not be found.
            </h1>
            <Button
              render={<Link to="/features" />}
              variant="brand"
              className="mt-8"
            >
              Back to modules
            </Button>
          </div>
        ) : feature.data ? (
          <>
            {/* HERO */}
            <section>
              <div className="mx-auto max-w-7xl px-6 py-20 sm:px-8 lg:py-28">
                <div className="grid grid-cols-12 gap-6">
                  <div className="col-span-12 lg:col-span-8">
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
                      Module
                    </span>
                    <h1
                      data-reveal
                      style={{ ["--reveal-delay" as string]: "120ms" }}
                      className="mt-4 font-serif text-[3rem] leading-[1.02] tracking-[-0.02em] sm:text-[4rem] lg:text-[4.5rem]"
                    >
                      {feature.data.title}
                    </h1>
                    <p
                      data-reveal
                      style={{ ["--reveal-delay" as string]: "240ms" }}
                      className="mt-6 max-w-3xl font-serif text-[1.5rem] italic leading-snug text-muted-foreground sm:text-[1.75rem]"
                    >
                      {feature.data.subtitle}
                    </p>
                  </div>
                  <div
                    className="col-span-12 lg:col-span-4 lg:pl-8"
                    data-reveal
                    style={{ ["--reveal-delay" as string]: "320ms" }}
                  >
                    <div className="rounded-[14px] border border-[color:var(--border)] bg-card p-6">
                      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                        At a glance
                      </p>
                      <dl className="mt-5 space-y-4 border-t border-[color:var(--border)] pt-5">
                        <div className="flex items-baseline justify-between">
                          <dt className="text-[12px] text-muted-foreground">
                            Status
                          </dt>
                          <dd
                            className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em]"
                            style={{
                              backgroundColor: "var(--brand-soft)",
                              color: "var(--brand-strong)",
                            }}
                          >
                            <span
                              aria-hidden
                              className="size-1 rounded-full animate-pulse-soft"
                              style={{
                                backgroundColor: "var(--brand-strong)",
                              }}
                            />
                            Production
                          </dd>
                        </div>
                        <div className="flex items-baseline justify-between">
                          <dt className="text-[12px] text-muted-foreground">
                            Capabilities
                          </dt>
                          <dd className="font-serif text-[1.5rem] tabular-nums">
                            {feature.data.capabilities.length}
                          </dd>
                        </div>
                        <div className="flex items-baseline justify-between">
                          <dt className="text-[12px] text-muted-foreground">
                            Steps
                          </dt>
                          <dd className="font-serif text-[1.5rem] tabular-nums">
                            {feature.data.how_it_works.length}
                          </dd>
                        </div>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* OVERVIEW */}
            <Section num="01" label="Overview" title="What this module does.">
              <p className="font-serif text-[1.5rem] leading-[1.4] tracking-[-0.005em] text-foreground sm:text-[1.75rem]">
                {feature.data.overview}
              </p>
            </Section>

            {/* CAPABILITIES */}
            <Section
              num="02"
              label="Capabilities"
              title="What you can do, specifically."
            >
              <ul className="divide-y divide-[color:var(--border)] border-y border-[color:var(--border)]">
                {feature.data.capabilities.map((c, i) => (
                  <li
                    key={c}
                    data-reveal
                    style={{ ["--reveal-delay" as string]: `${i * 60}ms` }}
                    className="grid grid-cols-12 gap-4 py-5 text-[14.5px] leading-[1.65]"
                  >
                    <span
                      className="col-span-2 font-mono text-[10px] uppercase tracking-[0.14em] sm:col-span-1"
                      style={{ color: "var(--brand-strong)" }}
                    >
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="col-span-10 sm:col-span-11">{c}</span>
                  </li>
                ))}
              </ul>
            </Section>

            {/* HOW IT WORKS */}
            {feature.data.how_it_works.length > 0 && (
              <Section
                num="03"
                label="Pipeline"
                title="How it actually runs."
              >
                <ol className="space-y-5">
                  {feature.data.how_it_works.map((step, i) => (
                    <li
                      key={step}
                      data-reveal
                      style={{ ["--reveal-delay" as string]: `${i * 80}ms` }}
                      className="group relative grid grid-cols-12 gap-4 overflow-hidden rounded-[14px] border border-[color:var(--border)] bg-card p-6 transition-all duration-300 hover:-translate-y-0.5 hover:border-[color:var(--brand)]/40 hover:shadow-[0_18px_40px_-22px_color-mix(in_oklch,var(--brand)_55%,transparent)]"
                    >
                      <span
                        aria-hidden
                        className="absolute inset-y-0 left-0 w-[3px] origin-top scale-y-0 transition-transform duration-500 ease-out group-hover:scale-y-100"
                        style={{ backgroundColor: "var(--brand)" }}
                      />
                      <span
                        className="col-span-2 font-serif text-[1.75rem] tabular-nums sm:col-span-1"
                        style={{ color: "var(--brand-strong)" }}
                      >
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <p className="col-span-10 self-center text-[14.5px] leading-[1.65] sm:col-span-11">
                        {step}
                      </p>
                    </li>
                  ))}
                </ol>
              </Section>
            )}

            {/* BENEFITS */}
            <Section
              num="04"
              label="Benefits"
              title="What you get out of the box."
            >
              <ul className="grid gap-3 sm:grid-cols-2">
                {feature.data.benefits.map((b, i) => (
                  <li
                    key={b}
                    data-reveal
                    style={{ ["--reveal-delay" as string]: `${i * 70}ms` }}
                    className="group flex items-start gap-3 rounded-[14px] border border-[color:var(--border)] bg-card p-5 text-[14px] leading-[1.6] transition-all duration-300 hover:-translate-y-0.5 hover:border-[color:var(--brand)]/40"
                  >
                    <span
                      className="mt-0.5 inline-flex size-5 shrink-0 items-center justify-center rounded-full transition-transform duration-300 group-hover:scale-110"
                      style={{
                        backgroundColor: "var(--brand)",
                        color: "var(--brand-foreground)",
                      }}
                    >
                      <Check className="size-3" strokeWidth={3} />
                    </span>
                    {b}
                  </li>
                ))}
              </ul>
            </Section>

            {/* CTA — solid brand slab */}
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
                    Next
                  </p>
                  <h2 className="mt-3 max-w-2xl font-serif text-[2.25rem] leading-[1.05] tracking-[-0.015em] sm:text-[2.75rem]">
                    Bring this module
                    <span
                      className="italic"
                      style={{
                        color:
                          "color-mix(in oklch, var(--brand-foreground) 80%, transparent)",
                      }}
                    >
                      {" "}
                      into your session.
                    </span>
                  </h2>
                </div>
                <div
                  className="flex items-center gap-4"
                  data-reveal
                  style={{ ["--reveal-delay" as string]: "120ms" }}
                >
                  <Button
                    render={<Link to="/features" />}
                    variant="ghost"
                    className="text-[color:var(--brand-foreground)] hover:bg-background/10 hover:text-[color:var(--brand-foreground)]"
                  >
                    All modules
                  </Button>
                  <Button
                    render={<Link to="/login" />}
                    size="lg"
                    className="h-11 rounded-md bg-card px-5 text-[14px] text-foreground hover:bg-background/90"
                  >
                    Sign in
                    <ArrowRight className="ml-1.5 size-4" strokeWidth={2.25} />
                  </Button>
                </div>
              </div>
            </section>
          </>
        ) : null}
      </main>

      <footer className="border-t border-[color:var(--border)] bg-background">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-4 px-6 py-8 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground sm:flex-row sm:items-center sm:px-8">
          <span>&copy; {new Date().getFullYear()} Ordo · All rights reserved.</span>
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
          </span>
        </div>
      </footer>
    </div>
  );
}
