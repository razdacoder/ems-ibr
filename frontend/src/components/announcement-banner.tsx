import { useState } from "react";
import { Info, TriangleAlert, X } from "lucide-react";
import { useSchoolPlan } from "@/api/school";
import { cn } from "@/lib/utils";

const DISMISSED_KEY = "ordo:dismissed-announcements";

function readDismissed(): number[] {
  try {
    const raw = window.localStorage.getItem(DISMISSED_KEY);
    return raw ? (JSON.parse(raw) as number[]) : [];
  } catch {
    return [];
  }
}

function saveDismissed(ids: number[]) {
  try {
    window.localStorage.setItem(DISMISSED_KEY, JSON.stringify(ids.slice(-20)));
  } catch {
    // Private mode or blocked storage: it just shows again next time.
  }
}

/**
 * Messages from the Ordo team (console Announcements), e.g. planned
 * maintenance. Information can be dismissed on this browser; warnings stay
 * until the team withdraws them or they end.
 */
export function AnnouncementBanner() {
  const plan = useSchoolPlan();
  const [dismissed, setDismissed] = useState<number[]>(() =>
    typeof window === "undefined" ? [] : readDismissed(),
  );
  const shown = (plan.data?.announcements ?? []).filter(
    (a) => a.level === "warning" || !dismissed.includes(a.id),
  );
  if (!shown.length) return null;

  return (
    <div className="shrink-0">
      {shown.map((a) => {
        const warning = a.level === "warning";
        const Icon = warning ? TriangleAlert : Info;
        return (
          <div
            key={a.id}
            role="status"
            className={cn(
              "flex items-start gap-3 border-b px-5 py-2.5 text-[13px] lg:px-12",
              warning
                ? "border-[color:var(--accent-amber-fg)]/30 bg-[color:var(--accent-amber)] text-[color:var(--accent-amber-fg)]"
                : "border-[color:var(--border)] bg-[color:var(--muted)] text-foreground",
            )}
          >
            <Icon className="mt-0.5 size-4 shrink-0" strokeWidth={2} aria-hidden />
            <p className="flex-1 whitespace-pre-line">{a.message}</p>
            {!warning && (
              <button
                type="button"
                aria-label="Dismiss"
                className="grid size-5 place-items-center text-muted-foreground hover:text-foreground"
                onClick={() => {
                  const next = [...dismissed, a.id];
                  setDismissed(next);
                  saveDismissed(next);
                }}
              >
                <X className="size-3.5" />
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
