import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import type { DirectorySlot } from "@/api/directory";

/** Anchor id for a slot section, used by the jump rail. */
export function slotId(slot: Pick<DirectorySlot, "date" | "period">) {
  return `slot-${slot.date}-${slot.period}`;
}

/** "Mon 12 May" for a YYYY-MM-DD string, read as a calendar date (no TZ shift). */
export function shortDate(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
    weekday: "short",
    day: "2-digit",
    month: "short",
  });
}

/** Small uppercase mono label used across the page. */
export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
      {children}
    </p>
  );
}

/** Figure + label, as on the hall allocation header. */
export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <Eyebrow>{label}</Eyebrow>
      <p className="mt-0.5 font-serif text-[1.5rem] leading-none tabular-nums">
        {value}
      </p>
    </div>
  );
}

/** Bordered button group for choosing one of a few values. */
export function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: T;
  options: { value: T; label: ReactNode }[];
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className="inline-flex items-center gap-1 border border-border bg-card p-1"
    >
      {options.map((o) => (
        <Button
          key={o.value}
          type="button"
          size="xs"
          variant={value === o.value ? "default" : "ghost"}
          aria-pressed={value === o.value}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </Button>
      ))}
    </div>
  );
}

/** Slot heading shared by both documents: title, date/period, then stats. */
export function SlotHeader({
  slot,
  stats,
}: {
  slot: DirectorySlot;
  stats: { label: string; value: ReactNode }[];
}) {
  return (
    <div className="flex flex-col gap-4 border-b border-[color:var(--border)] pb-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <Eyebrow>
          {shortDate(slot.date)} · {slot.period}
        </Eyebrow>
        <h2 className="mt-1.5 font-serif text-[1.35rem] leading-tight tracking-tight">
          {slot.title}
        </h2>
      </div>
      <div className="flex gap-6">
        {stats.map((s) => (
          <Stat key={s.label} label={s.label} value={s.value} />
        ))}
      </div>
    </div>
  );
}
