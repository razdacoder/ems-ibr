import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, useLocation, Navigate, Link } from "react-router-dom";
import { ArrowRight, Check, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useAuth } from "@/lib/auth";
import { extractErrorEnvelope } from "@/lib/api";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const { login, status } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [topError, setTopError] = useState<string | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  if (status === "authenticated") {
    return <Navigate to="/dashboard" replace />;
  }

  const onSubmit = async (values: FormValues) => {
    setTopError(null);
    try {
      await login(values.email, values.password);
      const redirectTo =
        (location.state as { from?: string } | null)?.from ?? "/dashboard";
      navigate(redirectTo, { replace: true });
    } catch (err) {
      const envelope = extractErrorEnvelope(err);
      setTopError(envelope.detail);
      if (envelope.errors) {
        for (const [field, messages] of Object.entries(envelope.errors)) {
          if (field === "email" || field === "password") {
            form.setError(field, { message: messages.join(", ") });
          }
        }
      }
    }
  };

  return (
    <div className="relative grid min-h-screen bg-background lg:grid-cols-[1.05fr_1fr]">
      {/* Editorial pane */}
      <div className="relative hidden overflow-hidden border-r border-[color:var(--border)] bg-[color:var(--muted)] lg:block">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(60% 50% at 80% 0%, rgba(149,100,0,0.06), transparent 60%), radial-gradient(50% 50% at 10% 90%, rgba(52,101,56,0.05), transparent 60%)",
          }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(0,0,0,1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,1) 1px, transparent 1px)",
            backgroundSize: "56px 56px",
            maskImage:
              "radial-gradient(60% 70% at 50% 50%, black, transparent 80%)",
          }}
        />

        <div className="relative flex h-full flex-col justify-between p-12 xl:p-16">
          <div className="flex items-center justify-between">
            <Link
              to="/"
              className="flex items-center gap-2 font-serif text-[1.5rem] tracking-tight"
            >
              <span
                aria-hidden
                className="inline-block size-2 rotate-45 bg-foreground"
              />
              ExamNova
            </Link>
            <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
              v4.2 · Mar 2026
            </span>
          </div>

          <div className="max-w-xl">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              § Sign in
            </p>
            <h2 className="mt-4 font-serif text-[2.75rem] leading-[1.05] tracking-[-0.02em] text-foreground xl:text-[3.25rem]">
              Run the exam season
              <br />
              <span className="italic text-muted-foreground">
                from one quiet room.
              </span>
            </h2>
            <p className="mt-6 max-w-md text-[15px] leading-[1.7] text-muted-foreground">
              Schedule, distribute, seat, and document — every step in one
              place, with live progress over WebSockets.
            </p>

            <ul className="mt-10 space-y-3.5">
              {[
                "Conflict-free timetable in under a minute",
                "Anti-cheating seat allocation with manual override",
                "DOCX, Excel, and CSV exports ready for the printer",
              ].map((line) => (
                <li
                  key={line}
                  className="flex items-start gap-3 text-[14px] text-foreground"
                >
                  <span className="mt-0.5 inline-flex size-4 items-center justify-center rounded-full bg-foreground/5">
                    <Check className="size-2.5" strokeWidth={3} />
                  </span>
                  {line}
                </li>
              ))}
            </ul>
          </div>

          <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
            <span>&copy; {new Date().getFullYear()} ExamNova</span>
            <span className="flex items-center gap-1.5">
              <Lock className="size-3" strokeWidth={2.25} />
              SOC 2 in progress · NDPR-aligned
            </span>
          </div>
        </div>
      </div>

      {/* Form pane */}
      <div className="flex flex-col">
        <div className="flex items-center justify-between border-b border-[color:var(--border)] px-6 py-5 lg:hidden">
          <Link
            to="/"
            className="flex items-center gap-2 font-serif text-[1.25rem] tracking-tight"
          >
            <span
              aria-hidden
              className="inline-block size-1.5 rotate-45 bg-foreground"
            />
            ExamNova
          </Link>
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
            v4.2
          </span>
        </div>

        <div className="flex flex-1 items-center justify-center px-6 py-16 lg:px-12">
          <div className="w-full max-w-[380px]">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              § Authenticate
            </p>
            <h1 className="mt-3 font-serif text-[2.25rem] leading-[1.05] tracking-[-0.015em]">
              Sign in.
            </h1>
            <p className="mt-3 text-[14px] leading-[1.65] text-muted-foreground">
              Use your work email and password. Need an account? Ask an
              administrator to invite you.
            </p>

            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="mt-10 space-y-5"
                noValidate
              >
                {topError && (
                  <Alert variant="destructive" className="border-[color:var(--accent-red-fg)]/20 bg-[color:var(--accent-red)]/40 text-[color:var(--accent-red-fg)]">
                    <AlertDescription>{topError}</AlertDescription>
                  </Alert>
                )}
                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                        Email
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="email"
                          autoComplete="email"
                          autoFocus
                          placeholder="you@university.edu"
                          className="h-11 rounded-md border-[color:var(--border)] bg-background"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                        Password
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="password"
                          autoComplete="current-password"
                          className="h-11 rounded-md border-[color:var(--border)] bg-background"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button
                  type="submit"
                  size="lg"
                  className="h-11 w-full rounded-md"
                  disabled={form.formState.isSubmitting}
                >
                  {form.formState.isSubmitting ? "Signing in…" : "Sign in"}
                  {!form.formState.isSubmitting && (
                    <ArrowRight className="ml-1.5 size-4" strokeWidth={2.25} />
                  )}
                </Button>
              </form>
            </Form>

            <div className="mt-12 flex items-center gap-3 border-t border-[color:var(--border)] pt-6 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
              <span className="relative inline-flex size-1.5">
                <span className="absolute inset-0 animate-ping rounded-full bg-[color:var(--accent-green-fg)]/60" />
                <span className="relative size-1.5 rounded-full bg-[color:var(--accent-green-fg)]" />
              </span>
              System nominal · 99.97% uptime · 90d
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
