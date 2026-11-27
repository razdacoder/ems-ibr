import { useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { AxiosError } from "axios";
import { ArrowRight, Check } from "lucide-react";
import { acceptInvite, fetchInvite, type InviteDetails } from "@/api/invites";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Skeleton } from "@/components/ui/skeleton";
import { InstitutionLogo } from "@/components/institution-logo";
import { Wordmark } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { extractErrorEnvelope } from "@/lib/api";
import { ROLE_LABELS, useAuth } from "@/lib/auth";

const LABEL = "font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground";

const schema = z
  .object({
    first_name: z.string().trim().min(1, "First name is required").max(30),
    last_name: z.string().trim().min(1, "Last name is required").max(30),
    password: z.string().min(8, "Use at least 8 characters"),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, {
    path: ["confirm"],
    message: "The passwords don't match",
  });

type Values = z.infer<typeof schema>;

function roleName(invite: InviteDetails): string {
  if (invite.role) return ROLE_LABELS[invite.role];
  return invite.department ? `Department Officer, ${invite.department.name}` : "Department Officer";
}

/** What the new account will be able to do, in plain words. */
function rolePoints(invite: InviteDetails): string[] {
  switch (invite.role) {
    case "SA":
      return [
        "Invite your team and manage who can sign in",
        "Generate the timetable, distribute halls and seat students",
        "Set the session, branding and exam documents",
      ];
    case "DO":
      return [
        "Upload courses, classes, halls and student lists",
        "Keep the exam data clean before generation",
        "Download exam documents",
      ];
    case "FO":
      return ["Manage faculties and their departments", "See the dashboard and exam documents"];
    case "ECM":
      return ["See the dashboard as the exam session runs", "Download exam documents"];
    default:
      return [
        `Look after ${invite.department?.name ?? "your department"}'s classes and students`,
        "See the timetable once it's published",
      ];
  }
}

/** Join a school from an emailed invite: set a name and password, then sign in. */
export default function InvitePage({ token }: { token: string }) {
  const invite = useQuery({
    queryKey: ["invite", token],
    queryFn: () => fetchInvite(token),
    retry: false,
    staleTime: Infinity,
  });
  const gone = invite.error instanceof AxiosError && invite.error.response?.status === 410;

  return (
    <div className="relative grid min-h-screen bg-background lg:grid-cols-[1.05fr_1fr]">
      <aside
        className="relative hidden overflow-hidden border-r border-[color:var(--border)] lg:block"
        style={{ backgroundColor: "var(--brand-soft)" }}
      >
        <div className="flex h-full flex-col justify-between p-12 xl:p-16">
          <Wordmark size="lg" />
          {invite.data ? (
            <div className="max-w-xl">
              <span
                className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.18em]"
                style={{ backgroundColor: "var(--brand)", color: "var(--brand-foreground)" }}
              >
                You're invited
              </span>
              <h2 className="mt-5 font-serif text-[2.75rem] leading-[1.02] tracking-[-0.02em] text-balance xl:text-[3.5rem]">
                Join {invite.data.school_name}
                <br />
                <span className="italic" style={{ color: "var(--brand-strong)" }}>
                  as {roleName(invite.data)}.
                </span>
              </h2>
              <ul className="mt-10 space-y-3.5">
                {rolePoints(invite.data).map((text) => (
                  <li key={text} className="flex items-start gap-3 text-[14px]">
                    <span
                      className="mt-0.5 inline-flex size-4 items-center justify-center rounded-full"
                      style={{ backgroundColor: "var(--brand)", color: "var(--brand-foreground)" }}
                    >
                      <Check className="size-2.5" strokeWidth={3} />
                    </span>
                    {text}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="max-w-xl">
              <h2 className="font-serif text-[2.75rem] leading-[1.02] tracking-[-0.02em] xl:text-[3.5rem]">
                Exam scheduling,
                <br />
                <span className="italic" style={{ color: "var(--brand-strong)" }}>
                  done together.
                </span>
              </h2>
            </div>
          )}
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
            &copy; {new Date().getFullYear()} Ordo
          </span>
        </div>
      </aside>

      <div className="relative flex flex-col">
        <div className="absolute right-4 top-4 z-10 hidden lg:block">
          <ThemeToggle size="sm" iconOnly />
        </div>
        <div className="flex items-center justify-between border-b border-[color:var(--border)] px-6 py-5 lg:hidden">
          <Wordmark />
          <ThemeToggle size="sm" iconOnly />
        </div>
        <div className="flex flex-1 items-center justify-center px-6 py-16 lg:px-12">
          <div className="w-full max-w-[400px]">
            <InstitutionLogo size={72} className="mb-8 flex" />
            {invite.isLoading ? (
              <div className="space-y-4" aria-busy="true">
                <Skeleton className="h-6 w-28" />
                <Skeleton className="h-10 w-3/4" />
                <Skeleton className="h-40 w-full" />
              </div>
            ) : gone ? (
              <Message
                eyebrow="Invite"
                title="This link no longer works."
                text="Invite links work once and expire after 7 days. Ask your administrator to send you a new one."
              >
                <Link to="/login" className={buttonVariants({ variant: "outline", className: "w-full" })}>
                  Go to sign in
                </Link>
              </Message>
            ) : invite.data ? (
              <AcceptForm token={token} invite={invite.data} />
            ) : (
              <Message
                eyebrow="Invite"
                title="We couldn't open this invite."
                text={extractErrorEnvelope(invite.error).detail}
              >
                <Button variant="outline" className="w-full" onClick={() => void invite.refetch()}>
                  Try again
                </Button>
              </Message>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Message({
  eyebrow,
  title,
  text,
  children,
}: {
  eyebrow: string;
  title: string;
  text: string;
  children: ReactNode;
}) {
  return (
    <>
      <Eyebrow>{eyebrow}</Eyebrow>
      <h1 className="mt-4 font-serif text-[2.25rem] leading-[1.05] tracking-[-0.02em]">{title}</h1>
      <p className="mt-3 text-[14.5px] leading-[1.65] text-muted-foreground">{text}</p>
      <div className="mt-8">{children}</div>
    </>
  );
}

function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.18em]"
      style={{ backgroundColor: "var(--brand-soft)", color: "var(--brand-strong)" }}
    >
      {children}
    </span>
  );
}

function AcceptForm({ token, invite }: { token: string; invite: InviteDetails }) {
  const { startSession } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [gone, setGone] = useState(false);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { first_name: "", last_name: "", password: "", confirm: "" },
  });

  const onSubmit = async ({ confirm: _confirm, ...values }: Values) => {
    setError(null);
    try {
      const session = await acceptInvite(token, values);
      startSession(session.token, session.user);
      navigate({ to: "/", replace: true });
    } catch (err) {
      if (err instanceof AxiosError && err.response?.status === 410) {
        setGone(true);
        return;
      }
      const envelope = extractErrorEnvelope(err);
      const errors = envelope.errors ?? {};
      for (const field of ["first_name", "last_name", "password"] as const) {
        if (errors[field]) form.setError(field, { message: errors[field].join(" ") });
      }
      if (!Object.keys(errors).length) setError(envelope.detail);
    }
  };

  if (gone) {
    return (
      <Message
        eyebrow="Invite"
        title="This link no longer works."
        text="It was used or replaced a moment ago. Ask your administrator to send you a new one."
      >
        <Link to="/login" className={buttonVariants({ variant: "outline", className: "w-full" })}>
          Go to sign in
        </Link>
      </Message>
    );
  }

  return (
    <>
      <Eyebrow>{invite.school_name}</Eyebrow>
      <h1 className="mt-4 font-serif text-[2.5rem] leading-[1.02] tracking-[-0.02em]">Set up your account.</h1>
      <p className="mt-3 text-[14px] leading-[1.65] text-muted-foreground">
        You'll sign in as <span className="font-medium text-foreground">{invite.email}</span>
        <span className="lg:hidden"> ({roleName(invite)})</span>.
      </p>
      {error && (
        <Alert variant="destructive" className="mt-6" role="alert">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="mt-8 space-y-5" noValidate>
          <div className="grid grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="first_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className={LABEL}>First name</FormLabel>
                  <FormControl>
                    <Input autoComplete="given-name" autoFocus className="h-11" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="last_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className={LABEL}>Last name</FormLabel>
                  <FormControl>
                    <Input autoComplete="family-name" className="h-11" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel className={LABEL}>Password</FormLabel>
                <FormControl>
                  <PasswordInput autoComplete="new-password" className="h-11" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="confirm"
            render={({ field }) => (
              <FormItem>
                <FormLabel className={LABEL}>Confirm password</FormLabel>
                <FormControl>
                  <PasswordInput autoComplete="new-password" className="h-11" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" variant="brand" size="lg" className="w-full" disabled={form.formState.isSubmitting}>
            {form.formState.isSubmitting ? "Setting up…" : "Join and sign in"}
            <ArrowRight data-icon="inline-end" strokeWidth={2.25} />
          </Button>
        </form>
      </Form>
    </>
  );
}
