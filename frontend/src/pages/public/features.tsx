import { Link } from "react-router-dom";
import { ArrowUpRight, ArrowRight } from "lucide-react";
import { useFeatures } from "@/api/public";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const ACCENTS = [
  { bg: "bg-[color:var(--accent-green)]", fg: "text-[color:var(--accent-green-fg)]" },
  { bg: "bg-[color:var(--accent-blue)]", fg: "text-[color:var(--accent-blue-fg)]" },
  { bg: "bg-[color:var(--accent-yellow)]", fg: "text-[color:var(--accent-yellow-fg)]" },
  { bg: "bg-[color:var(--accent-red)]", fg: "text-[color:var(--accent-red-fg)]" },
];

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
          <Link to="/features" className="text-foreground">
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

function PublicFooter() {
  return (
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
          <Link to="/login" className="hover:text-foreground">
            Sign in
          </Link>
        </span>
      </div>
    </footer>
  );
}

export default function FeaturesPage() {
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
                <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  § Index — Modules
                </p>
                <h1 className="mt-4 font-serif text-[3rem] leading-[1.02] tracking-[-0.02em] sm:text-[4rem] lg:text-[4.75rem]">
                  Every module
                  <br />
                  the platform <span className="italic">ships</span> with.
                </h1>
              </div>
              <div className="col-span-12 lg:col-span-5 lg:pl-8">
                <p className="text-[15px] leading-[1.7] text-muted-foreground">
                  ExamNova is a deliberately small surface — five modules, one
                  pipeline, one source of truth. Each module owns one job and
                  emits its progress over a typed event stream so the rest of
                  the system never has to guess.
                </p>
                <div className="mt-6 flex items-center gap-4">
                  <Button render={<Link to="/login" />} size="lg" className="h-11">
                    Open the dashboard
                    <ArrowRight className="ml-1.5 size-4" strokeWidth={2.25} />
                  </Button>
                  <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                    v4.2 · Mar 2026
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* INDEX LIST */}
        <section className="bg-[color:var(--muted)]">
          <div className="mx-auto max-w-7xl px-6 py-16 sm:px-8 lg:py-24">
            <div className="mb-10 flex items-end justify-between">
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                § 01 — Index
              </p>
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
                {features.data?.map((f, i) => {
                  const accent = ACCENTS[i % ACCENTS.length];
                  return (
                    <Link
                      key={f.slug}
                      to={`/features/${f.slug}`}
                      className="group relative flex flex-col justify-between gap-6 rounded-[12px] border border-[color:var(--border)] bg-background p-7 transition-all duration-300 hover:-translate-y-px hover:border-foreground/20"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <span
                          className={`inline-block rounded-full ${accent.bg} px-2.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] ${accent.fg}`}
                        >
                          Module · {String(i + 1).padStart(2, "0")}
                        </span>
                        <ArrowUpRight
                          className="size-4 text-muted-foreground transition-all duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-foreground"
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
                  );
                })}
              </div>
            )}
          </div>
        </section>

        {/* CTA */}
        <section className="border-t border-[color:var(--border)] bg-foreground text-background">
          <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-8 px-6 py-16 sm:flex-row sm:items-center sm:px-8 lg:py-20">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-background/60">
                Ready when you are
              </p>
              <h2 className="mt-3 max-w-2xl font-serif text-[2.25rem] leading-[1.05] tracking-[-0.015em] sm:text-[2.75rem]">
                Open the dashboard
                <span className="italic text-background/80"> and start a season.</span>
              </h2>
            </div>
            <Button
              render={<Link to="/login" />}
              size="lg"
              className="h-11 rounded-md bg-background text-foreground hover:bg-background/90"
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
