import { useEffect, useRef, useState } from "react";
import { redeemSupportTicket } from "@/api/school";
import { Wordmark } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { extractErrorEnvelope, setSupportExpiry, setToken } from "@/lib/api";

/*
 * Where the console's one time support link lands: <slug>.<base>/support?ticket=…
 * The ticket is swapped for a support token, then the dashboard opens.
 */
export default function SupportPage({ ticket }: { ticket?: string }) {
  const [error, setError] = useState<string | null>(
    ticket ? null : "This support link is incomplete.",
  );
  // The ticket works once; StrictMode's second effect run must not spend it again.
  const spent = useRef(false);

  useEffect(() => {
    if (!ticket || spent.current) return;
    spent.current = true;
    // Keep the ticket out of browser history.
    window.history.replaceState(null, "", "/support");
    redeemSupportTicket(ticket)
      .then(({ token, expires_at }) => {
        setToken(token);
        setSupportExpiry(expires_at);
        window.location.replace("/");
      })
      .catch((err) => setError(extractErrorEnvelope(err).detail));
  }, [ticket]);

  return (
    <main className="relative flex min-h-screen flex-col bg-background">
      <div className="flex items-center justify-between p-6">
        <Wordmark size="md" />
        <ThemeToggle size="sm" iconOnly />
      </div>
      <div className="flex flex-1 items-center justify-center px-6 pb-24">
        <div className="max-w-md text-center" aria-live="polite">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            Ordo support
          </p>
          <h1 className="mt-4 font-serif text-[2.25rem] leading-[1.05] tracking-[-0.02em] text-foreground text-balance">
            {error ? "Link no longer works" : "Opening the school…"}
          </h1>
          <p className="mt-4 text-[15px] leading-[1.7] text-muted-foreground">
            {error
              ? `${error} Start a new support session from the console.`
              : "Starting your support session. This takes a moment."}
          </p>
        </div>
      </div>
    </main>
  );
}
