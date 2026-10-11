import { useEffect, useState } from "react";
import { LifeBuoy } from "lucide-react";
import { endSupportSession, useSchoolPlan } from "@/api/school";
import { Button } from "@/components/ui/button";
import { clearToken } from "@/lib/api";

/** "mm:ss" left until ``expiresAt``, never below zero. */
export function timeLeft(expiresAt: string, now: number): string {
  const seconds = Math.max(0, Math.floor((Date.parse(expiresAt) - now) / 1000));
  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

function signOut() {
  clearToken();
  window.location.assign("/login");
}

/**
 * Shown while an Ordo support token is in use (spec 0003, child 0006): who
 * is in, how long is left, and a way out. Signs out when the time is up; the
 * server has already stopped accepting the token by then.
 */
export function SupportBanner() {
  const plan = useSchoolPlan();
  const support = plan.data?.support;
  const [now, setNow] = useState(() => Date.now());
  const [ending, setEnding] = useState(false);

  useEffect(() => {
    if (!support) return;
    const tick = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(tick);
  }, [support]);

  const expired = !!support && Date.parse(support.expires_at) <= now;
  useEffect(() => {
    if (expired) signOut();
  }, [expired]);

  if (!support?.active) return null;

  const end = async () => {
    setEnding(true);
    try {
      await endSupportSession();
    } catch {
      // Already ended or expired: the token is unusable either way.
    }
    signOut();
  };

  return (
    <div
      role="status"
      className="flex shrink-0 flex-wrap items-center justify-between gap-x-4 gap-y-2 bg-brand px-5 py-2 text-[13px] text-brand-foreground lg:px-12"
    >
      <p className="flex items-center gap-2">
        <LifeBuoy className="size-4 shrink-0" strokeWidth={2} aria-hidden />
        <span>
          Ordo support session ({support.admin_name}), ends in{" "}
          <span className="font-medium tabular-nums">{timeLeft(support.expires_at, now)}</span>
        </span>
      </p>
      <Button
        size="sm"
        variant="outline"
        className="h-7 border-brand-foreground/40 bg-transparent text-brand-foreground hover:bg-brand-foreground/10 hover:text-brand-foreground"
        disabled={ending}
        onClick={() => void end()}
      >
        {ending ? "Ending…" : "End session"}
      </Button>
    </div>
  );
}
