import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowRight,
  Plus,
  Minus,
  Check,
  Lock,
} from "lucide-react";
import { Button } from "@/components/ui/button";

/* -----------------------------------------------------------
 * ExamNova — Editorial Landing
 * Premium utilitarian minimalism. Warm bone canvas, editorial
 * serif headlines, monospace meta-data, asymmetric bento.
 * --------------------------------------------------------- */

const STATS = [
  { value: "27,020", label: "students seated", meta: "FY 25/26" },
  { value: "1,171", label: "courses scheduled", meta: "across 12 faculties" },
  { value: "70", label: "halls supported", meta: "incl. annex blocks" },
  { value: "<1s", label: "to live progress events", meta: "p95 WebSocket" },
];

const PIPELINE = [
  {
    n: "01",
    label: "Ingest",
    body: "Upload departments, halls, classes, students. Validate, lock.",
    detail: "CSV · strict schema",
  },
  {
    n: "02",
    label: "Schedule",
    body: "Generate the timetable. Honour AM/PM splits and CBE/PBE rules.",
    detail: "14s · 248 classes",
  },
  {
    n: "03",
    label: "Distribute",
    body: "Hall capacity solver assigns rooms. Splits where required.",
    detail: "8s · capacity-aware",
  },
  {
    n: "04",
    label: "Allocate",
    body: "Seat students with 8-direction adjacency anti-cheating rules.",
    detail: "47s · seat-by-seat",
  },
  {
    n: "05",
    label: "Export",
    body: "Print-ready DOCX, broadsheet Excel, per-department CSV.",
    detail: "3s · reproducible",
  },
];

const FAQS = [
  {
    q: "How does the scheduler avoid clashes?",
    a: "It treats each student's class catalog as a hard constraint and never schedules two of their courses in the same window. AM/PM splits, Sundays, and CBE/PBE separation are encoded as additional constraints rather than post-hoc filters.",
  },
  {
    q: "What happens after a generation run?",
    a: "Ingestion is locked for that exam season. The generated artefacts (timetable, distribution, allocation, broadsheet) are versioned together so any later report can be reproduced from the same source of truth.",
  },
  {
    q: "Can a department override a seat assignment?",
    a: "Yes. The allocation view exposes a manual override for unplaced students or specific seats. The override is logged with the operator's name and the original suggestion is preserved for audit.",
  },
  {
    q: "How are large classes split across halls?",
    a: "The distribution solver looks at hall utilisation per slot, splits oversize classes across rooms while keeping invigilation overhead minimal, and reports the final utilisation back to the dashboard.",
  },
  {
    q: "What does the live progress stream actually show?",
    a: "A WebSocket feed emits a structured event per stage (queued, started, progress %, completed, failed). The dashboard subscribes per job and lets you retry from the failed stage rather than from scratch.",
  },
];

/* --- Inline editorial illustration: continuous-line plus pastel shape --- */
function GridSketch() {
  return (
    <svg
      viewBox="0 0 200 140"
      className="h-auto w-full"
      aria-hidden
      fill="none"
    >
      <circle cx="142" cy="44" r="30" fill="var(--accent-yellow)" />
      <path
        d="M20 116 C 40 60, 80 38, 130 50 C 170 60, 184 92, 174 116"
        stroke="var(--foreground)"
        strokeWidth="1.25"
        strokeLinecap="round"
      />
      <path
        d="M20 116 L 184 116"
        stroke="var(--foreground)"
        strokeWidth="1.25"
        strokeLinecap="round"
      />
      {Array.from({ length: 7 }).map((_, i) => (
        <circle
          key={i}
          cx={32 + i * 24}
          cy={116 - Math.sin(i * 0.7) * 10 - 14}
          r="2"
          fill="var(--foreground)"
        />
      ))}
    </svg>
  );
}

function SeatGridSketch() {
  const rows = 6;
  const cols = 9;
  const cell = 18;
  const pad = 10;
  return (
    <svg
      viewBox={`0 0 ${cols * cell + pad * 2} ${rows * cell + pad * 2 + 18}`}
      className="h-auto w-full"
      aria-hidden
    >
      <rect
        x="0.5"
        y="0.5"
        width={cols * cell + pad * 2 - 1}
        height={rows * cell + pad * 2 + 17}
        rx="6"
        fill="var(--card)"
        stroke="var(--border)"
      />
      <text
        x={pad}
        y={14}
        fontFamily="JetBrains Mono, monospace"
        fontSize="7"
        letterSpacing="0.06em"
        fill="var(--muted-foreground)"
      >
        HALL · CBN · SLOT 02
      </text>
      {Array.from({ length: rows }).map((_, r) =>
        Array.from({ length: cols }).map((_, c) => {
          const filled = (r + c) % 3 !== 0;
          const accent = r === 2 && c === 4;
          return (
            <rect
              key={`${r}-${c}`}
              x={pad + c * cell + 2}
              y={20 + r * cell + 2}
              width={cell - 4}
              height={cell - 4}
              rx="2"
              fill={
                accent
                  ? "var(--accent-green)"
                  : filled
                    ? "var(--muted)"
                    : "var(--card)"
              }
              stroke={accent ? "var(--accent-green-fg)" : "var(--border)"}
              strokeWidth={accent ? 1.2 : 1}
            />
          );
        }),
      )}
    </svg>
  );
}

function CalendarSketch() {
  const days = ["M", "T", "W", "T", "F", "S"];
  const cells = Array.from({ length: 30 }, (_, i) => i + 1);
  const slots: Record<number, "am" | "pm" | "both"> = {
    3: "am",
    5: "pm",
    9: "both",
    10: "am",
    14: "pm",
    16: "am",
    20: "both",
    23: "pm",
    27: "am",
  };
  return (
    <div className="rounded-md border border-border bg-card p-4">
      <div className="grid grid-cols-6 gap-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
        {days.map((d, i) => (
          <span key={i}>{d}</span>
        ))}
      </div>
      <div className="mt-2 grid grid-cols-6 gap-1">
        {cells.map((n) => {
          const s = slots[n];
          return (
            <div
              key={n}
              className="relative aspect-square rounded-[3px] border border-border bg-background p-1"
            >
              <span className="font-mono text-[9px] text-muted-foreground">{n}</span>
              {s === "am" && (
                <span className="absolute inset-x-1 bottom-1 h-1 rounded-[1px] bg-[color:var(--accent-yellow)]" />
              )}
              {s === "pm" && (
                <span className="absolute inset-x-1 bottom-1 h-1 rounded-[1px] bg-[color:var(--accent-blue)]" />
              )}
              {s === "both" && (
                <>
                  <span className="absolute inset-x-1 bottom-2.5 h-1 rounded-[1px] bg-[color:var(--accent-yellow)]" />
                  <span className="absolute inset-x-1 bottom-1 h-1 rounded-[1px] bg-[color:var(--accent-blue)]" />
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* --- Faux-OS window chrome --- */
function WindowChrome({
  title,
  meta,
  children,
}: {
  title: string;
  meta?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-[12px] border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border bg-background px-4 py-2.5">
        <div className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-border" />
          <span className="size-2.5 rounded-full bg-border" />
          <span className="size-2.5 rounded-full bg-border" />
        </div>
        <div className="flex items-baseline gap-3 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          <span>{title}</span>
          {meta && <span className="hidden sm:inline">{meta}</span>}
        </div>
        <span className="size-2.5" />
      </div>
      {children}
    </div>
  );
}

/* --- Reveal hook --- */
function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll<HTMLElement>("[data-reveal]");
    if (!("IntersectionObserver" in window)) {
      els.forEach((el) => el.classList.add("is-visible"));
      return;
    }
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add("is-visible");
            obs.unobserve(e.target);
          }
        }
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.05 },
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);
}

/* --- FAQ accordion item --- */
function FaqItem({ q, a, idx }: { q: string; a: string; idx: number }) {
  const [open, setOpen] = useState(idx === 0);
  return (
    <div className="border-b border-border">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="group flex w-full items-start justify-between gap-6 py-7 text-left"
      >
        <span className="font-serif text-xl leading-snug text-foreground sm:text-[1.625rem]">
          {q}
        </span>
        <span className="mt-1 inline-flex size-7 shrink-0 items-center justify-center rounded-full border border-border text-foreground transition-colors group-hover:bg-muted">
          {open ? (
            <Minus className="size-3.5" strokeWidth={2} />
          ) : (
            <Plus className="size-3.5" strokeWidth={2} />
          )}
        </span>
      </button>
      <div
        className="grid overflow-hidden transition-all duration-500 ease-out"
        style={{
          gridTemplateRows: open ? "1fr" : "0fr",
          opacity: open ? 1 : 0,
        }}
      >
        <div className="min-h-0">
          <p className="max-w-3xl pb-7 text-[15px] leading-[1.7] text-muted-foreground">
            {a}
          </p>
        </div>
      </div>
    </div>
  );
}

/* --- Live status pill (animated dot, mono text) --- */
function LiveStatus() {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-[color:var(--accent-green-fg)]">
      <span className="relative inline-flex size-1.5">
        <span className="absolute inset-0 animate-ping rounded-full bg-[color:var(--accent-green-fg)]/60" />
        <span className="relative size-1.5 rounded-full bg-[color:var(--accent-green-fg)]" />
      </span>
      System nominal
    </span>
  );
}

export default function LandingPage() {
  useReveal();
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-background text-foreground antialiased">
      {/* Ambient drift layer — radial warmth, very faint */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          background:
            "radial-gradient(60% 50% at 80% 0%, rgba(149,100,0,0.05) 0%, transparent 60%), radial-gradient(50% 50% at 10% 30%, rgba(52,101,56,0.04) 0%, transparent 60%)",
        }}
      />
      <div
        aria-hidden
        className="ambient-drift pointer-events-none fixed inset-0 -z-10 opacity-60"
        style={{
          backgroundImage:
            "radial-gradient(40% 30% at 30% 80%, rgba(31,108,159,0.04) 0%, transparent 70%)",
        }}
      />

      {/* ============================ HEADER ============================ */}
      <header className="sticky top-0 z-40 border-b border-border/80 bg-background/70 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6 sm:px-8">
          <Link
            to="/"
            className="flex items-center gap-2 font-serif text-[1.25rem] tracking-tight"
          >
            <span
              aria-hidden
              className="inline-block size-2 rotate-45 bg-foreground"
            />
            ExamNova
          </Link>

          <nav className="hidden items-center gap-8 text-[13px] text-muted-foreground md:flex">
            <Link to="/features" className="hover:text-foreground">
              Modules
            </Link>
            <a href="#pipeline" className="hover:text-foreground">
              Pipeline
            </a>
            <a href="#evidence" className="hover:text-foreground">
              Evidence
            </a>
            <a href="#faq" className="hover:text-foreground">
              FAQ
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <LiveStatus />
            <Button
              render={<Link to="/login" />}
              size="sm"
              className="rounded-md bg-foreground text-background hover:bg-foreground/85"
            >
              Sign in
              <ArrowUpRight className="ml-1 size-3.5" strokeWidth={2.25} />
            </Button>
          </div>
        </div>
      </header>

      <main>
        {/* ============================ HERO ============================ */}
        <section className="relative">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-border to-transparent"
          />
          <div className="mx-auto max-w-7xl px-6 pb-20 pt-16 sm:px-8 sm:pt-24 lg:pb-32 lg:pt-32">
            <div className="grid gap-16 lg:grid-cols-12 lg:gap-12">
              <div className="lg:col-span-7" data-reveal>
                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center gap-2 rounded-full bg-[color:var(--accent-yellow)] px-3 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--accent-yellow-fg)]">
                    <span className="size-1 rounded-full bg-[color:var(--accent-yellow-fg)]" />
                    Operations OS for examinations
                  </span>
                  <span className="hidden font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground sm:inline">
                    v4.2 · Mar 2026
                  </span>
                </div>

                <h1 className="mt-8 font-serif text-[3rem] leading-[1.02] tracking-[-0.02em] text-foreground sm:text-[4.25rem] lg:text-[5.25rem]">
                  Run the entire
                  <br />
                  <span className="italic text-foreground">exam season </span>
                  from
                  <br />
                  <span className="relative inline-block">
                    one quiet room.
                    <svg
                      aria-hidden
                      viewBox="0 0 320 18"
                      className="absolute -bottom-2 left-0 h-3 w-full"
                      fill="none"
                    >
                      <path
                        d="M2 13 C 80 4, 200 4, 318 12"
                        stroke="var(--accent-green-fg)"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                      />
                    </svg>
                  </span>
                </h1>

                <p className="mt-8 max-w-2xl text-[1.0625rem] leading-[1.7] text-foreground/85">
                  ExamNova schedules, distributes, seats, and documents every
                  exam — without spreadsheets and without weekend war rooms. Job
                  progress streams over WebSockets. Ingestion locks after the
                  first generation, so reports stay reproducible months later.
                </p>

                <div className="mt-10 flex flex-wrap items-center gap-4">
                  <Button
                    render={<Link to="/login" />}
                    size="lg"
                    className="h-11 rounded-md bg-foreground px-5 text-[14px] text-background hover:bg-foreground/85"
                  >
                    Open the dashboard
                    <ArrowRight className="ml-1.5 size-4" strokeWidth={2.25} />
                  </Button>
                  <Link
                    to="/features"
                    className="group inline-flex items-center gap-1.5 text-[14px] font-medium text-foreground"
                  >
                    See every module
                    <span className="relative inline-block h-px w-0 bg-foreground transition-all duration-300 group-hover:w-5" />
                    <ArrowUpRight
                      className="size-4 transition-transform group-hover:-translate-y-px group-hover:translate-x-px"
                      strokeWidth={2.25}
                    />
                  </Link>
                </div>

                <div className="mt-12 flex flex-wrap items-center gap-x-6 gap-y-3 font-mono text-[11px] uppercase tracking-[0.1em] text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <Lock className="size-3" strokeWidth={2.25} />
                    Source-locked after generation
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Check className="size-3" strokeWidth={2.5} />
                    No spreadsheet exports required
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Check className="size-3" strokeWidth={2.5} />
                    Built for ≥ 1,000 student cohorts
                  </span>
                </div>
              </div>

              {/* Hero right: faux generation window */}
              <div
                className="lg:col-span-5"
                data-reveal
                style={{ ["--reveal-delay" as string]: "120ms" }}
              >
                <WindowChrome
                  title="examnova/jobs"
                  meta="run #20260316-AM"
                >
                  <div className="space-y-5 px-6 py-6">
                    <div className="flex items-baseline justify-between">
                      <p className="font-serif text-[1.25rem] tracking-tight">
                        Generation timeline
                      </p>
                      <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-[color:var(--accent-green-fg)]">
                        Done · 1m 12s
                      </p>
                    </div>
                    <ol className="space-y-3.5">
                      {[
                        { name: "Ingest", dur: "—", state: "lock", pct: 100 },
                        { name: "Timetable", dur: "14s", state: "ok", pct: 100 },
                        {
                          name: "Distribution",
                          dur: "8s",
                          state: "ok",
                          pct: 100,
                        },
                        {
                          name: "Allocation",
                          dur: "47s",
                          state: "ok",
                          pct: 100,
                        },
                        {
                          name: "Broadsheet",
                          dur: "3s",
                          state: "ok",
                          pct: 100,
                        },
                      ].map((s) => (
                        <li key={s.name}>
                          <div className="flex items-center justify-between text-[13px]">
                            <span className="flex items-center gap-2">
                              <span className="inline-flex size-4 items-center justify-center rounded-full bg-[color:var(--accent-green)] text-[color:var(--accent-green-fg)]">
                                {s.state === "lock" ? (
                                  <Lock
                                    className="size-2.5"
                                    strokeWidth={2.5}
                                  />
                                ) : (
                                  <Check
                                    className="size-2.5"
                                    strokeWidth={3}
                                  />
                                )}
                              </span>
                              <span className="font-medium text-foreground">
                                {s.name}
                              </span>
                            </span>
                            <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
                              {s.dur}
                            </span>
                          </div>
                          <div className="mt-2 h-[3px] w-full overflow-hidden rounded-full bg-muted">
                            <div
                              className="h-full bg-foreground"
                              style={{ width: `${s.pct}%` }}
                            />
                          </div>
                        </li>
                      ))}
                    </ol>

                    <div className="grid grid-cols-3 gap-3 border-t border-border pt-5">
                      {[
                        { k: "Halls", v: "70" },
                        { k: "Classes", v: "248" },
                        { k: "Conflicts", v: "0" },
                      ].map((m) => (
                        <div key={m.k}>
                          <p className="font-serif text-2xl tabular-nums">
                            {m.v}
                          </p>
                          <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                            {m.k}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </WindowChrome>

                <div className="mt-4 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                  <span>Last run · 2026-03-16 06:42 WAT</span>
                  <span className="flex items-center gap-1.5 text-[color:var(--accent-green-fg)]">
                    <span className="size-1 rounded-full bg-[color:var(--accent-green-fg)]" />
                    Streamed live
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ============================ STAT STRIP ============================ */}
        <section className="border-y border-border bg-card">
          <div className="mx-auto max-w-7xl px-6 sm:px-8">
            <div className="grid grid-cols-2 lg:grid-cols-4">
              {STATS.map((s, i) => (
                <div
                  key={s.label}
                  className={
                    "py-10 lg:py-12 " +
                    (i !== 0 ? "lg:border-l lg:border-border lg:pl-10 " : "") +
                    (i % 2 !== 0 ? "border-l border-border pl-6 lg:pl-10 " : "pr-6 ") +
                    (i < 2 ? "border-b border-border lg:border-b-0 " : "")
                  }
                  data-reveal
                  style={{
                    ["--reveal-delay" as string]: `${i * 80}ms`,
                  }}
                >
                  <p className="font-serif text-[2.5rem] leading-none tabular-nums text-foreground sm:text-[3.25rem]">
                    {s.value}
                  </p>
                  <p className="mt-3 text-[13px] text-foreground">{s.label}</p>
                  <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                    {s.meta}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ============================ MANIFESTO ============================ */}
        <section className="relative">
          <div className="mx-auto max-w-5xl px-6 py-28 sm:px-8 lg:py-40">
            <div className="grid grid-cols-12 items-start gap-6">
              <div className="col-span-12 sm:col-span-3 lg:col-span-2">
                <p
                  className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground"
                  data-reveal
                >
                  § 01
                  <br />
                  Position
                </p>
              </div>
              <blockquote
                className="col-span-12 sm:col-span-9 lg:col-span-10"
                data-reveal
                style={{ ["--reveal-delay" as string]: "100ms" }}
              >
                <p className="font-serif text-[1.75rem] leading-[1.25] tracking-[-0.01em] text-foreground sm:text-[2.5rem] lg:text-[3rem]">
                  Examinations are a logistics problem disguised as an academic
                  one.{" "}
                  <span className="text-muted-foreground">
                    A thousand small decisions — which course at which hour, in
                    which hall, with which student in which seat — compound
                    into the difference between a quiet week and a war room.
                  </span>{" "}
                  ExamNova exists so the quiet week is the default.
                </p>
                <footer className="mt-10 flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
                  <span className="h-px w-10 bg-foreground" />
                  Engineering note · ExamNova team
                </footer>
              </blockquote>
            </div>
          </div>
        </section>

        {/* ============================ BENTO ============================ */}
        <section className="bg-card">
          <div className="mx-auto max-w-7xl px-6 py-24 sm:px-8 lg:py-32">
            <div className="mb-14 flex flex-wrap items-end justify-between gap-6">
              <div data-reveal>
                <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                  § 02 — Modules
                </p>
                <h2 className="mt-3 max-w-3xl font-serif text-[2.25rem] leading-[1.05] tracking-[-0.015em] text-foreground sm:text-[3rem]">
                  Every step from upload to attendance sheet.
                </h2>
              </div>
              <Link
                to="/features"
                className="group inline-flex items-center gap-1.5 text-[13px] text-foreground"
                data-reveal
              >
                Open the index
                <ArrowUpRight
                  className="size-3.5 transition-transform group-hover:-translate-y-px group-hover:translate-x-px"
                  strokeWidth={2.25}
                />
              </Link>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
              {/* CARD 1 — Scheduling, large with calendar mock */}
              <article
                className="group relative col-span-1 flex flex-col justify-between overflow-hidden rounded-[12px] border border-border bg-card p-7 transition-all duration-300 hover:-translate-y-px sm:col-span-2 lg:col-span-4 lg:row-span-2"
                style={{ minHeight: 360 }}
                data-reveal
              >
                <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
                  <div className="max-w-md">
                    <span className="inline-block rounded-full bg-[color:var(--accent-green)] px-2.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-[color:var(--accent-green-fg)]">
                      Scheduling
                    </span>
                    <h3 className="mt-4 font-serif text-[1.75rem] leading-[1.1] tracking-[-0.01em] sm:text-[2rem]">
                      Conflict-free timetables in minutes.
                    </h3>
                    <p className="mt-3 text-[14px] leading-[1.65] text-muted-foreground">
                      Pick the exam window. The scheduler honours class
                      catalogs, AM/PM splits, and CBE/PBE separation, and
                      excludes Sundays automatically.
                    </p>
                  </div>
                </div>
                <div className="mt-6">
                  <CalendarSketch />
                  <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                    Avg. run · 14s for 248 classes across 70 halls
                  </p>
                </div>
              </article>

              {/* CARD 2 — Distribution */}
              <article
                className="col-span-1 flex flex-col gap-4 rounded-[12px] border border-border bg-card p-7 sm:col-span-2"
                data-reveal
                style={{ ["--reveal-delay" as string]: "60ms" }}
              >
                <span className="inline-block self-start rounded-full bg-[color:var(--accent-blue)] px-2.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-[color:var(--accent-blue-fg)]">
                  Distribution
                </span>
                <h3 className="font-serif text-[1.5rem] leading-tight tracking-[-0.01em]">
                  Capacity-aware hall assignment.
                </h3>
                <p className="text-[13.5px] leading-[1.65] text-muted-foreground">
                  Large classes split across halls. Small ones share. Utilisation
                  reported per slot.
                </p>
                <div className="mt-auto flex items-end gap-1 pt-4">
                  {[68, 92, 74, 88, 81, 95, 70].map((h, i) => (
                    <div
                      key={i}
                      className="flex-1 rounded-t-[2px] bg-foreground/85"
                      style={{ height: `${h * 0.6}px` }}
                    />
                  ))}
                </div>
                <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                  utilisation · slot-by-slot
                </p>
              </article>

              {/* CARD 3 — Seating with grid sketch */}
              <article
                className="col-span-1 flex flex-col gap-4 rounded-[12px] border border-border bg-card p-7 sm:col-span-2"
                data-reveal
                style={{ ["--reveal-delay" as string]: "120ms" }}
              >
                <span className="inline-block self-start rounded-full bg-[color:var(--accent-red)] px-2.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-[color:var(--accent-red-fg)]">
                  Seating
                </span>
                <h3 className="font-serif text-[1.5rem] leading-tight tracking-[-0.01em]">
                  Anti-cheating seat placement.
                </h3>
                <p className="text-[13.5px] leading-[1.65] text-muted-foreground">
                  8-direction adjacency rules with manual override for unplaced
                  students.
                </p>
                <div className="mt-2">
                  <SeatGridSketch />
                </div>
              </article>

              {/* CARD 4 — Reports */}
              <article
                className="col-span-1 flex flex-col gap-4 rounded-[12px] border border-border bg-card p-7 sm:col-span-2"
                data-reveal
              >
                <span className="inline-block self-start rounded-full bg-[color:var(--accent-yellow)] px-2.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-[color:var(--accent-yellow-fg)]">
                  Reports
                </span>
                <h3 className="font-serif text-[1.5rem] leading-tight tracking-[-0.01em]">
                  Print-ready exports.
                </h3>
                <p className="text-[13.5px] leading-[1.65] text-muted-foreground">
                  DOCX attendance sheets, broadsheet Excel, per-department CSV.
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {["DOCX", "XLSX", "CSV", "PDF"].map((f) => (
                    <kbd
                      key={f}
                      className="rounded-[4px] border border-border bg-muted px-2 py-1 font-mono text-[10px] tracking-wider text-foreground"
                    >
                      {f}
                    </kbd>
                  ))}
                </div>
              </article>

              {/* CARD 5 — Ingestion (DARK accent) */}
              <article
                className="relative col-span-1 flex flex-col gap-4 overflow-hidden rounded-[12px] border border-foreground bg-foreground p-7 text-background sm:col-span-2"
                data-reveal
                style={{ ["--reveal-delay" as string]: "60ms" }}
              >
                <span className="inline-block self-start rounded-full bg-background/10 px-2.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-background/70">
                  Ingestion
                </span>
                <h3 className="font-serif text-[1.5rem] leading-tight tracking-[-0.01em] text-background">
                  Bulk CSV uploads. Locked after generation.
                </h3>
                <p className="text-[13.5px] leading-[1.65] text-background/65">
                  Strict validation. Versioned per season. The source of truth
                  stays clean.
                </p>
                <div className="mt-3 rounded-[6px] border border-background/10 bg-black/40 p-3 font-mono text-[11px] leading-relaxed text-background/80">
                  <span className="text-[color:var(--accent-yellow-fg)]">$</span> examnova ingest
                  ./roster.csv
                  <br />
                  <span className="text-background/50">→</span> 27,020 rows · 0
                  warnings · sealed
                </div>
              </article>

              {/* CARD 6 — Monitoring */}
              <article
                className="col-span-1 flex flex-col gap-4 rounded-[12px] border border-border bg-card p-7 sm:col-span-2"
                data-reveal
                style={{ ["--reveal-delay" as string]: "120ms" }}
              >
                <span className="inline-block self-start rounded-full bg-[color:var(--accent-green)] px-2.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-[color:var(--accent-green-fg)]">
                  Monitoring
                </span>
                <h3 className="font-serif text-[1.5rem] leading-tight tracking-[-0.01em]">
                  Live job progress.
                </h3>
                <p className="text-[13.5px] leading-[1.65] text-muted-foreground">
                  WebSocket stream while jobs run. Retry from the failed stage.
                </p>
                <div className="relative mt-2 h-12 overflow-hidden rounded-[6px] bg-muted">
                  <div
                    aria-hidden
                    className="absolute inset-y-0 left-0 w-2/3 bg-foreground transition-all"
                  />
                  <span className="relative z-10 flex h-full items-center px-3 font-mono text-[10px] uppercase tracking-[0.14em] text-background">
                    Allocation · 67%
                  </span>
                </div>
              </article>
            </div>
          </div>
        </section>

        {/* ============================ PIPELINE ============================ */}
        <section id="pipeline" className="relative border-t border-border">
          <div className="mx-auto max-w-7xl px-6 py-24 sm:px-8 lg:py-32">
            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 lg:col-span-4" data-reveal>
                <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                  § 03 — Pipeline
                </p>
                <h2 className="mt-3 font-serif text-[2.25rem] leading-[1.05] tracking-[-0.015em] sm:text-[2.75rem]">
                  Five stages,
                  <br />
                  <span className="italic">one source of truth.</span>
                </h2>
                <p className="mt-5 max-w-md text-[15px] leading-[1.65] text-muted-foreground">
                  Each stage produces a versioned artefact and emits a
                  WebSocket event. Re-run any stage in isolation; the rest
                  remain valid.
                </p>
                <div className="mt-8 hidden lg:block">
                  <GridSketch />
                </div>
              </div>

              <div className="col-span-12 lg:col-span-8">
                <ol className="divide-y divide-border border-y border-border">
                  {PIPELINE.map((p, i) => (
                    <li
                      key={p.n}
                      className="group grid grid-cols-12 gap-4 py-6 transition-colors sm:gap-6"
                      data-reveal
                      style={{
                        ["--reveal-delay" as string]: `${i * 80}ms`,
                      }}
                    >
                      <span className="col-span-2 font-serif text-[1.5rem] tabular-nums text-muted-foreground sm:col-span-1">
                        {p.n}
                      </span>
                      <div className="col-span-10 sm:col-span-4">
                        <p className="font-serif text-[1.5rem] leading-tight tracking-[-0.01em]">
                          {p.label}
                        </p>
                        <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                          {p.detail}
                        </p>
                      </div>
                      <p className="col-span-12 max-w-xl text-[14px] leading-[1.65] text-foreground/85 sm:col-span-7">
                        {p.body}
                      </p>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          </div>
        </section>

        {/* ============================ EVIDENCE / BROADSHEET ============================ */}
        <section
          id="evidence"
          className="relative overflow-hidden bg-muted"
        >
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{
              backgroundImage:
                "radial-gradient(40% 60% at 100% 0%, rgba(31,108,159,0.05), transparent 70%)",
            }}
          />
          <div className="relative mx-auto max-w-7xl px-6 py-24 sm:px-8 lg:py-32">
            <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
              <div className="lg:col-span-5" data-reveal>
                <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                  § 04 — Evidence
                </p>
                <h2 className="mt-3 font-serif text-[2.25rem] leading-[1.05] tracking-[-0.015em] sm:text-[2.75rem]">
                  The broadsheet, generated.
                </h2>
                <p className="mt-5 text-[15px] leading-[1.7] text-foreground/85">
                  A single document captures every student's allocation across
                  the season — hall, seat, slot, course code. Reproducible from
                  the locked source data, exportable to Excel and PDF on demand.
                </p>

                <dl className="mt-10 grid grid-cols-2 gap-x-6 gap-y-6 border-t border-border pt-8">
                  {[
                    { k: "Generation time", v: "1m 12s" },
                    { k: "Conflicts found", v: "0" },
                    { k: "Halls utilised", v: "62 / 70" },
                    { k: "Manual overrides", v: "3" },
                  ].map((d) => (
                    <div key={d.k}>
                      <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                        {d.k}
                      </dt>
                      <dd className="mt-1.5 font-serif text-[1.75rem] tabular-nums text-foreground">
                        {d.v}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>

              <div
                className="lg:col-span-7"
                data-reveal
                style={{ ["--reveal-delay" as string]: "120ms" }}
              >
                <WindowChrome
                  title="examnova/broadsheet"
                  meta="20260316_AM.xlsx"
                >
                  <div className="overflow-hidden">
                    <div className="border-b border-border bg-card px-5 py-3">
                      <div className="grid grid-cols-12 gap-3 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                        <span className="col-span-3">Mat. No</span>
                        <span className="col-span-3">Course</span>
                        <span className="col-span-2">Hall</span>
                        <span className="col-span-2">Seat</span>
                        <span className="col-span-2 text-right">Slot</span>
                      </div>
                    </div>
                    <ul className="divide-y divide-border bg-card">
                      {[
                        ["IBR/CSC/22/0142", "CSC301", "CBN", "B-07", "AM-2"],
                        ["IBR/CSC/22/0143", "CSC301", "CBN", "B-08", "AM-2"],
                        ["IBR/MTH/22/0098", "MTH205", "ANNEX-A", "C-12", "AM-1"],
                        ["IBR/ENG/21/0211", "ENG410", "MAIN-2", "D-04", "PM-1"],
                        ["IBR/PHY/22/0067", "PHY120", "CBN", "A-01", "PM-2"],
                        ["IBR/PHY/22/0068", "PHY120", "CBN", "A-03", "PM-2"],
                        ["IBR/CHM/23/0019", "CHM110", "ANNEX-B", "E-09", "AM-1"],
                        ["IBR/ACC/22/0301", "ACC202", "MAIN-1", "F-15", "PM-1"],
                      ].map((row, i) => (
                        <li
                          key={i}
                          className="grid grid-cols-12 gap-3 px-5 py-3 font-mono text-[12px] tabular-nums text-foreground"
                        >
                          <span className="col-span-3 text-foreground">
                            {row[0]}
                          </span>
                          <span className="col-span-3 text-foreground/85">
                            {row[1]}
                          </span>
                          <span className="col-span-2 text-foreground/85">
                            {row[2]}
                          </span>
                          <span className="col-span-2">
                            <kbd className="rounded-[3px] border border-border bg-muted px-1.5 py-0.5 text-[10px]">
                              {row[3]}
                            </kbd>
                          </span>
                          <span className="col-span-2 text-right text-muted-foreground">
                            {row[4]}
                          </span>
                        </li>
                      ))}
                    </ul>
                    <div className="flex items-center justify-between border-t border-border bg-background px-5 py-3 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                      <span>showing 8 of 27,020</span>
                      <span className="flex items-center gap-1.5 text-[color:var(--accent-green-fg)]">
                        <Lock className="size-3" strokeWidth={2.25} />
                        Sealed · 2026-03-16
                      </span>
                    </div>
                  </div>
                </WindowChrome>
              </div>
            </div>
          </div>
        </section>

        {/* ============================ TRUST MARQUEE ============================ */}
        <section className="border-y border-border bg-card py-12">
          <div className="mx-auto max-w-7xl px-6 sm:px-8">
            <p className="text-center font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              In production at universities and polytechnics
            </p>
            <div className="relative mt-6 overflow-hidden">
              <div
                aria-hidden
                className="pointer-events-none absolute inset-y-0 left-0 z-10 w-24 bg-gradient-to-r from-card to-transparent"
              />
              <div
                aria-hidden
                className="pointer-events-none absolute inset-y-0 right-0 z-10 w-24 bg-gradient-to-l from-card to-transparent"
              />
              <div className="marquee-track flex w-max items-center gap-16">
                {[
                  ...[
                    "Ibadan Polytechnic",
                    "Federal Univ. Oye-Ekiti",
                    "Lagos State Univ.",
                    "Univ. of Ilorin",
                    "Obafemi Awolowo Univ.",
                    "Yaba College of Tech.",
                    "Univ. of Benin",
                  ],
                  ...[
                    "Ibadan Polytechnic",
                    "Federal Univ. Oye-Ekiti",
                    "Lagos State Univ.",
                    "Univ. of Ilorin",
                    "Obafemi Awolowo Univ.",
                    "Yaba College of Tech.",
                    "Univ. of Benin",
                  ],
                ].map((name, i) => (
                  <span
                    key={i}
                    className="font-serif text-[1.5rem] italic text-muted-foreground"
                  >
                    {name}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ============================ FAQ ============================ */}
        <section id="faq" className="bg-background">
          <div className="mx-auto max-w-5xl px-6 py-24 sm:px-8 lg:py-32">
            <div className="grid grid-cols-12 gap-6">
              <div className="col-span-12 lg:col-span-4" data-reveal>
                <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                  § 05 — Questions
                </p>
                <h2 className="mt-3 font-serif text-[2.25rem] leading-[1.05] tracking-[-0.015em] sm:text-[2.75rem]">
                  The five most
                  <br />
                  <span className="italic">asked things.</span>
                </h2>
                <p className="mt-5 text-[14px] leading-[1.65] text-muted-foreground">
                  Anything missing?{" "}
                  <a
                    href="mailto:hello@examnova.app"
                    className="text-foreground underline underline-offset-4 decoration-border hover:decoration-foreground"
                  >
                    Write to us
                  </a>
                  .
                </p>
              </div>
              <div
                className="col-span-12 lg:col-span-8"
                data-reveal
                style={{ ["--reveal-delay" as string]: "100ms" }}
              >
                <div className="border-t border-border">
                  {FAQS.map((f, i) => (
                    <FaqItem key={i} q={f.q} a={f.a} idx={i} />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ============================ CTA ============================ */}
        <section className="relative overflow-hidden border-t border-border bg-foreground text-background">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 opacity-60"
            style={{
              backgroundImage:
                "radial-gradient(50% 60% at 80% 20%, rgba(251,243,219,0.06), transparent 65%), radial-gradient(40% 50% at 10% 80%, rgba(225,243,254,0.05), transparent 65%)",
            }}
          />
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{
              backgroundImage:
                "linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)",
              backgroundSize: "56px 56px",
              maskImage:
                "radial-gradient(60% 70% at 50% 40%, black, transparent 80%)",
            }}
          />
          <div className="relative mx-auto max-w-5xl px-6 py-28 text-center sm:px-8 lg:py-40">
            <p
              className="font-mono text-[10px] uppercase tracking-[0.18em] text-background/60"
              data-reveal
            >
              Ready when you are
            </p>
            <h2
              className="mx-auto mt-6 max-w-3xl font-serif text-[2.5rem] leading-[1.05] tracking-[-0.015em] sm:text-[4rem] lg:text-[5rem]"
              data-reveal
              style={{ ["--reveal-delay" as string]: "100ms" }}
            >
              Cut your exam season
              <br />
              <span className="italic text-background/85">
                from a month to an afternoon.
              </span>
            </h2>
            <div
              className="mt-12 flex flex-col items-center justify-center gap-5 sm:flex-row sm:gap-6"
              data-reveal
              style={{ ["--reveal-delay" as string]: "200ms" }}
            >
              <Button
                render={<Link to="/login" />}
                size="lg"
                className="h-12 rounded-md bg-card px-6 text-[14px] text-foreground hover:bg-background/90"
              >
                Sign in to the dashboard
                <ArrowRight className="ml-1.5 size-4" strokeWidth={2.25} />
              </Button>
              <Link
                to="/features"
                className="group inline-flex items-center gap-1.5 text-[14px] font-medium text-background/85 hover:text-background"
              >
                Read the module index
                <ArrowUpRight
                  className="size-4 transition-transform group-hover:-translate-y-px group-hover:translate-x-px"
                  strokeWidth={2.25}
                />
              </Link>
            </div>

            <div
              className="mt-16 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 font-mono text-[10px] uppercase tracking-[0.14em] text-background/50"
              data-reveal
              style={{ ["--reveal-delay" as string]: "300ms" }}
            >
              <span>v4.2 · Mar 2026</span>
              <span>SOC 2 type II in progress</span>
              <span>NDPR-aligned</span>
              <span>Single-tenant deployments</span>
            </div>
          </div>
        </section>

        {/* ============================ FOOTER ============================ */}
        <footer className="border-t border-border bg-background">
          <div className="mx-auto max-w-7xl px-6 sm:px-8">
            <div className="grid grid-cols-2 gap-10 py-16 sm:grid-cols-12">
              <div className="col-span-2 sm:col-span-5">
                <Link
                  to="/"
                  className="flex items-center gap-2 font-serif text-[1.5rem] tracking-tight text-foreground"
                >
                  <span
                    aria-hidden
                    className="inline-block size-2 rotate-45 bg-foreground"
                  />
                  ExamNova
                </Link>
                <p className="mt-4 max-w-sm text-[13.5px] leading-[1.65] text-muted-foreground">
                  Operations OS for examinations. Schedule, distribute, seat,
                  document — without the spreadsheets.
                </p>
                <div className="mt-6 flex items-center gap-3">
                  <LiveStatus />
                  <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                    99.97% uptime · 90d
                  </span>
                </div>
              </div>

              <div className="sm:col-span-2">
                <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                  Product
                </p>
                <ul className="mt-4 space-y-2.5 text-[13.5px] text-foreground">
                  <li>
                    <Link to="/features" className="hover:text-[color:var(--accent-green-fg)]">
                      Modules
                    </Link>
                  </li>
                  <li>
                    <a href="#pipeline" className="hover:text-[color:var(--accent-green-fg)]">
                      Pipeline
                    </a>
                  </li>
                  <li>
                    <a href="#evidence" className="hover:text-[color:var(--accent-green-fg)]">
                      Evidence
                    </a>
                  </li>
                  <li>
                    <Link to="/login" className="hover:text-[color:var(--accent-green-fg)]">
                      Dashboard
                    </Link>
                  </li>
                </ul>
              </div>

              <div className="sm:col-span-2">
                <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                  Resources
                </p>
                <ul className="mt-4 space-y-2.5 text-[13.5px] text-foreground">
                  <li>
                    <a href="#faq" className="hover:text-[color:var(--accent-green-fg)]">
                      FAQ
                    </a>
                  </li>
                  <li>Documentation</li>
                  <li>Release notes</li>
                  <li>Status</li>
                </ul>
              </div>

              <div className="sm:col-span-3">
                <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                  Contact
                </p>
                <ul className="mt-4 space-y-2.5 text-[13.5px] text-foreground">
                  <li>
                    <a
                      href="mailto:hello@examnova.app"
                      className="hover:text-[color:var(--accent-green-fg)]"
                    >
                      hello@examnova.app
                    </a>
                  </li>
                  <li className="text-muted-foreground">
                    Mokola, Ibadan
                    <br />
                    Oyo State, Nigeria
                  </li>
                </ul>
              </div>
            </div>

            <div className="flex flex-col items-start justify-between gap-3 border-t border-border py-6 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground sm:flex-row sm:items-center">
              <span>
                &copy; {new Date().getFullYear()} ExamNova · All rights
                reserved.
              </span>
              <span className="flex flex-wrap items-center gap-x-6 gap-y-1">
                <span>Privacy</span>
                <span>Terms</span>
                <span>Security</span>
                <span>NDPR Notice</span>
              </span>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
