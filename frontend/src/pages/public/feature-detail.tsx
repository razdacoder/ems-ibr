import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowUpRight, ArrowRight, Check } from "lucide-react";
import { useFeature } from "@/api/public";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

function PublicHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-[color:var(--border)] bg-background/70 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6 sm:px-8">
        <Link
          to="/"
          className="flex items-center gap-2 font-serif text-[1.25rem] tracking-tight"
        >
          <span aria-hidden className="inline-block size-2 rotate-45 bg-foreground" />
          ExamNova
        </Link>
        <nav className="hidden items-center gap-7 text-[13px] text-muted-foreground md:flex">
          <Link to="/" className="hover:text-foreground">
            Home
          </Link>
          <Link to="/features" className="hover:text-foreground">
            Modules
          </Link>
        </nav>
        <Button render={<Link to="/login" />} size="sm">
          Sign in
          <ArrowUpRight className="ml-1 size-3.5" strokeWidth={2.25} />
        </Button>
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
        <div className="col-span-12 lg:col-span-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            § {num} — {label}
          </p>
          <h2 className="mt-3 font-serif text-[2rem] leading-[1.05] tracking-[-0.015em] sm:text-[2.5rem]">
            {title}
          </h2>
        </div>
        <div className="col-span-12 lg:col-span-8 lg:pl-8">{children}</div>
      </div>
    </section>
  );
}

export default function FeatureDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const feature = useFeature(slug);

  return (
    <div className="min-h-screen bg-background text-foreground antialiased">
      <PublicHeader />

      <main>
        {/* Crumb */}
        <div className="border-b border-[color:var(--border)] bg-[color:var(--muted)]/40">
          <div className="mx-auto flex max-w-7xl items-center gap-4 px-6 py-4 text-[12px] text-muted-foreground sm:px-8">
            <Link
              to="/features"
              className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] hover:text-foreground"
            >
              <ArrowLeft className="size-3" strokeWidth={2.25} />
              All modules
            </Link>
            <span aria-hidden className="text-muted-foreground/40">
              /
            </span>
            <span className="font-mono text-[10px] uppercase tracking-[0.14em]">
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
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
              404 · Not found
            </p>
            <h1 className="mt-4 font-serif text-[2.5rem] tracking-[-0.015em]">
              That module could not be found.
            </h1>
            <Button render={<Link to="/features" />} className="mt-8">
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
                    <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                      § Module
                    </p>
                    <h1 className="mt-4 font-serif text-[3rem] leading-[1.02] tracking-[-0.02em] sm:text-[4rem] lg:text-[4.5rem]">
                      {feature.data.title}
                    </h1>
                    <p className="mt-6 max-w-3xl font-serif text-[1.5rem] italic leading-snug text-muted-foreground sm:text-[1.75rem]">
                      {feature.data.subtitle}
                    </p>
                  </div>
                  <div className="col-span-12 lg:col-span-4 lg:pl-8">
                    <div className="rounded-[12px] border border-[color:var(--border)] bg-background p-6">
                      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                        At a glance
                      </p>
                      <dl className="mt-5 space-y-4 border-t border-[color:var(--border)] pt-5">
                        <div className="flex items-baseline justify-between">
                          <dt className="text-[12px] text-muted-foreground">Status</dt>
                          <dd className="font-mono text-[11px] uppercase tracking-[0.12em] text-[color:var(--accent-green-fg)]">
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
                          <dt className="text-[12px] text-muted-foreground">Steps</dt>
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
                    className="grid grid-cols-12 gap-4 py-5 text-[14.5px] leading-[1.65]"
                  >
                    <span className="col-span-2 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground sm:col-span-1">
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
                      className="grid grid-cols-12 gap-4 rounded-[12px] border border-[color:var(--border)] bg-background p-6"
                    >
                      <span className="col-span-2 font-serif text-[1.75rem] tabular-nums text-muted-foreground sm:col-span-1">
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
                {feature.data.benefits.map((b) => (
                  <li
                    key={b}
                    className="flex items-start gap-3 rounded-[12px] border border-[color:var(--border)] bg-background p-5 text-[14px] leading-[1.6]"
                  >
                    <span className="mt-0.5 inline-flex size-5 shrink-0 items-center justify-center rounded-full bg-[color:var(--accent-green)] text-[color:var(--accent-green-fg)]">
                      <Check className="size-3" strokeWidth={3} />
                    </span>
                    {b}
                  </li>
                ))}
              </ul>
            </Section>

            {/* CTA */}
            <section className="border-t border-[color:var(--border)] bg-foreground text-background">
              <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-8 px-6 py-16 sm:flex-row sm:items-center sm:px-8 lg:py-20">
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-background/60">
                    Next
                  </p>
                  <h2 className="mt-3 max-w-2xl font-serif text-[2.25rem] leading-[1.05] tracking-[-0.015em] sm:text-[2.75rem]">
                    Bring this module
                    <span className="italic text-background/80"> into your season.</span>
                  </h2>
                </div>
                <div className="flex items-center gap-4">
                  <Button render={<Link to="/features" />} variant="ghost" className="text-background hover:bg-background/10 hover:text-background">
                    All modules
                  </Button>
                  <Button
                    render={<Link to="/login" />}
                    size="lg"
                    className="h-11 rounded-md bg-background text-foreground hover:bg-background/90"
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
          <span>&copy; {new Date().getFullYear()} ExamNova · All rights reserved.</span>
          <span className="flex items-center gap-6">
            <Link to="/" className="hover:text-foreground">
              Home
            </Link>
            <Link to="/features" className="hover:text-foreground">
              Modules
            </Link>
          </span>
        </div>
      </footer>
    </div>
  );
}
