import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, useLocation, Navigate, Link } from "react-router-dom";
import { ArrowRight, Check } from "lucide-react";
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
import { ThemeToggle } from "@/components/theme-toggle";
import { Logo } from "@/components/logo";

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
      {/* Editorial pane — solid purple-soft */}
      <div
        className="relative hidden overflow-hidden border-r border-[color:var(--border)] lg:block"
        style={{ backgroundColor: "var(--brand-soft)" }}
      >
        <div className="relative flex h-full flex-col justify-between p-12 xl:p-16">
          <div className="flex items-center justify-between">
            <Link
              to="/"
              className="flex items-center gap-2 font-serif text-[1.5rem] tracking-tight"
            >
              <Logo size={22} />
              AuraSchedule
            </Link>
          </div>

          <div className="max-w-xl">
            <span
              className="animate-fade-up inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.18em]"
              style={{
                backgroundColor: "var(--brand)",
                color: "var(--brand-foreground)",
                ["--anim-delay" as string]: "60ms",
              }}
            >
              <span
                aria-hidden
                className="size-1 rounded-full animate-pulse-soft"
                style={{ backgroundColor: "var(--brand-foreground)" }}
              />
              Sign in
            </span>
            <h2
              className="animate-fade-up mt-5 font-serif text-[2.75rem] leading-[1.02] tracking-[-0.02em] text-foreground text-balance xl:text-[3.5rem]"
              style={{ ["--anim-delay" as string]: "140ms" }}
            >
              Run the exam session
              <br />
              <span className="italic" style={{ color: "var(--brand-strong)" }}>
                from one quiet room.
              </span>
            </h2>
            <p
              className="animate-fade-up mt-6 max-w-md text-[15px] leading-[1.7] text-muted-foreground"
              style={{ ["--anim-delay" as string]: "240ms" }}
            >
              Schedule, distribute, seat, and document — every step in one
              place, with live progress over WebSockets.
            </p>

            <ul className="mt-10 space-y-3.5">
              {[
                "Conflict-free timetable in under a minute",
                "Anti-cheating seat allocation with manual override",
                "DOCX, Excel, and CSV exports ready for the printer",
              ].map((text, i) => (
                <li
                  key={text}
                  className="animate-fade-up flex items-start gap-3 text-[14px] text-foreground"
                  style={{
                    ["--anim-delay" as string]: `${340 + i * 90}ms`,
                  }}
                >
                  <span
                    className="mt-0.5 inline-flex size-4 items-center justify-center rounded-full"
                    style={{
                      backgroundColor: "var(--brand)",
                      color: "var(--brand-foreground)",
                    }}
                  >
                    <Check className="size-2.5" strokeWidth={3} />
                  </span>
                  {text}
                </li>
              ))}
            </ul>
          </div>

          <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
            <span>&copy; {new Date().getFullYear()} AuraSchedule</span>
          </div>
        </div>
      </div>

      {/* Form pane */}
      <div className="relative flex flex-col">
        {/* Theme toggle — anchored top-right of the form pane on desktop */}
        <div className="absolute right-4 top-4 z-10 hidden lg:block">
          <ThemeToggle size="sm" iconOnly />
        </div>
        <div className="flex items-center justify-between border-b border-[color:var(--border)] px-6 py-5 lg:hidden">
          <Link
            to="/"
            className="flex items-center gap-2 font-serif text-[1.25rem] tracking-tight"
          >
            <Logo size={18} />
            AuraSchedule
          </Link>
          <div className="flex items-center gap-2">
            <ThemeToggle size="sm" iconOnly />
          </div>
        </div>

        <div className="flex flex-1 items-center justify-center px-6 py-16 lg:px-12">
          <div className="w-full max-w-[380px]">
            <span
              className="animate-fade-up inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.18em]"
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
              Authenticate
            </span>
            <h1
              className="animate-fade-up mt-4 font-serif text-[2.5rem] leading-[1.02] tracking-[-0.02em]"
              style={{ ["--anim-delay" as string]: "80ms" }}
            >
              Sign in.
            </h1>
            <p
              className="animate-fade-up mt-3 text-[14px] leading-[1.65] text-muted-foreground"
              style={{ ["--anim-delay" as string]: "180ms" }}
            >
              Use your work email and password. Need an account? Ask an
              administrator to invite you.
            </p>

            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="animate-fade-up mt-10 space-y-5"
                style={{ ["--anim-delay" as string]: "260ms" }}
                noValidate
              >
                {topError && (
                  <Alert variant="destructive" className="border-[color:var(--destructive)]/30 bg-[color:var(--destructive)]/10 text-[color:var(--destructive)]">
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
                  variant="brand"
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

          </div>
        </div>
      </div>
    </div>
  );
}
