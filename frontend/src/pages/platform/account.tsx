import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Laptop, LogOut } from "lucide-react";
import {
  type PlatformSession,
  useChangePassword,
  useConfirmReenrol,
  useMySessions,
  useRevokeOtherSessions,
  useRevokeSession,
  useStartReenrol,
} from "@/api/platform";
import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Skeleton } from "@/components/ui/skeleton";
import { extractErrorEnvelope } from "@/lib/api";
import { useConfirm } from "@/lib/confirm";
import { PLATFORM_ROLE_LABELS, usePlatformAuth } from "@/lib/platform-auth";
import { toast } from "@/lib/use-toast";
import { EnrolmentCode } from "./login";

/** Put the API's field errors on the form; returns the detail when none matched. */
function applyErrors<T extends string>(
  err: unknown,
  fields: readonly T[],
  setError: (field: T, error: { message: string }) => void,
): string | null {
  const envelope = extractErrorEnvelope(err);
  const errors = envelope.errors ?? {};
  let matched = false;
  for (const field of fields) {
    if (errors[field]) {
      setError(field, { message: errors[field].join(" ") });
      matched = true;
    }
  }
  return matched ? null : envelope.detail;
}

/* ---------------------------------------------------------------- password */

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Enter your current password."),
    new_password: z.string().min(12, "Use at least 12 characters."),
    confirm: z.string(),
  })
  .refine((v) => v.new_password === v.confirm, {
    path: ["confirm"],
    message: "The two passwords don't match.",
  });

function PasswordCard() {
  const change = useChangePassword();
  const [error, setError] = useState<string | null>(null);
  const form = useForm<z.infer<typeof passwordSchema>>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: "", new_password: "", confirm: "" },
  });

  const onSubmit = async (values: z.infer<typeof passwordSchema>) => {
    setError(null);
    try {
      await change.mutateAsync({
        current_password: values.current_password,
        new_password: values.new_password,
      });
      form.reset();
      toast({ title: "Password changed", description: "Your other sessions were signed out." });
    } catch (err) {
      setError(applyErrors(err, ["current_password", "new_password"] as const, form.setError));
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Password</CardTitle>
        <CardDescription>Changing it signs you out everywhere except here.</CardDescription>
      </CardHeader>
      <CardContent>
        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="grid max-w-md gap-4" noValidate>
            <FormField
              control={form.control}
              name="current_password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Current password</FormLabel>
                  <FormControl>
                    <PasswordInput autoComplete="current-password" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="new_password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>New password</FormLabel>
                  <FormControl>
                    <PasswordInput autoComplete="new-password" {...field} />
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
                  <FormLabel>New password again</FormLabel>
                  <FormControl>
                    <PasswordInput autoComplete="new-password" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div>
              <Button type="submit" disabled={change.isPending}>
                Change password
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

/* ---------------------------------------------------------------- authenticator */

const startSchema = z.object({
  current_password: z.string().min(1, "Enter your password."),
  code: z.string().regex(/^\d{6}$/, "Enter the 6 digit code."),
});
const confirmSchema = z.object({ code: z.string().regex(/^\d{6}$/, "Enter the 6 digit code.") });

function AuthenticatorCard() {
  const start = useStartReenrol();
  const confirm = useConfirmReenrol();
  const [pending, setPending] = useState<{ challenge: string; otpauth_uri: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const startForm = useForm<z.infer<typeof startSchema>>({
    resolver: zodResolver(startSchema),
    defaultValues: { current_password: "", code: "" },
  });
  const confirmForm = useForm<z.infer<typeof confirmSchema>>({
    resolver: zodResolver(confirmSchema),
    defaultValues: { code: "" },
  });

  const cancel = () => {
    setPending(null);
    setError(null);
    startForm.reset();
    confirmForm.reset();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Authenticator app</CardTitle>
        <CardDescription>
          Move two step sign in to a new phone or app. Your current one keeps working until the new
          one is confirmed.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {!pending ? (
          <Form {...startForm}>
            <form
              noValidate
              className="grid max-w-md gap-4"
              onSubmit={startForm.handleSubmit(async (values) => {
                setError(null);
                try {
                  setPending(await start.mutateAsync(values));
                } catch (err) {
                  setError(applyErrors(err, ["current_password", "code"] as const, startForm.setError));
                }
              })}
            >
              <FormField
                control={startForm.control}
                name="current_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <PasswordInput autoComplete="current-password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={startForm.control}
                name="code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Code from your current app</FormLabel>
                    <FormControl>
                      <Input inputMode="numeric" autoComplete="one-time-code" maxLength={6} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div>
                <Button type="submit" disabled={start.isPending}>
                  Set up a new app
                </Button>
              </div>
            </form>
          </Form>
        ) : (
          <div className="grid max-w-md gap-4">
            <p className="text-[13.5px] text-muted-foreground">
              Scan this with the new app, then enter the code it shows.
            </p>
            <EnrolmentCode uri={pending.otpauth_uri} />
            <Form {...confirmForm}>
              <form
                noValidate
                className="grid gap-4"
                onSubmit={confirmForm.handleSubmit(async ({ code }) => {
                  setError(null);
                  try {
                    await confirm.mutateAsync({ challenge: pending.challenge, code });
                    toast({ title: "Authenticator changed", description: "Use the new app from now on." });
                    cancel();
                  } catch (err) {
                    setError(applyErrors(err, ["code"] as const, confirmForm.setError));
                  }
                })}
              >
                <FormField
                  control={confirmForm.control}
                  name="code"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Code from the new app</FormLabel>
                      <FormControl>
                        <Input inputMode="numeric" autoComplete="one-time-code" maxLength={6} {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="flex gap-2">
                  <Button type="submit" disabled={confirm.isPending}>
                    Confirm
                  </Button>
                  <Button type="button" variant="outline" onClick={cancel}>
                    Cancel
                  </Button>
                </div>
              </form>
            </Form>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ---------------------------------------------------------------- sessions */

/** "Chrome on macOS" from a user agent, good enough to tell devices apart. */
export function describeAgent(ua: string): string {
  if (!ua) return "Unknown device";
  const browser = /Edg\//.test(ua)
    ? "Edge"
    : /Firefox\//.test(ua)
      ? "Firefox"
      : /Chrome\//.test(ua)
        ? "Chrome"
        : /Safari\//.test(ua)
          ? "Safari"
          : "Browser";
  const os = /iPhone|iPad/.test(ua)
    ? "iOS"
    : /Android/.test(ua)
      ? "Android"
      : /Mac OS X/.test(ua)
        ? "macOS"
        : /Windows/.test(ua)
          ? "Windows"
          : /Linux/.test(ua)
            ? "Linux"
            : "an unknown system";
  return `${browser} on ${os}`;
}

function when(iso: string | null) {
  if (!iso) return "never";
  return new Date(iso).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function SessionRow({ session }: { session: PlatformSession }) {
  const revoke = useRevokeSession();
  return (
    <li className="flex items-center gap-4 px-5 py-3">
      <Laptop className="size-4 shrink-0 text-muted-foreground" aria-hidden />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-[13.5px] font-medium">
          {describeAgent(session.user_agent)}
          {session.current && <Badge>This device</Badge>}
        </div>
        <p className="truncate font-mono text-[11px] text-muted-foreground">
          {session.ip ?? "unknown address"} · signed in {when(session.created_at)} · last used{" "}
          {when(session.last_used_at)}
        </p>
      </div>
      {!session.current && (
        <Button
          variant="outline"
          size="sm"
          disabled={revoke.isPending}
          onClick={async () => {
            try {
              await revoke.mutateAsync(session.id);
              toast({ title: "Session ended" });
            } catch (err) {
              toast({
                title: "That didn't work",
                description: extractErrorEnvelope(err).detail,
                variant: "destructive",
              });
            }
          }}
        >
          Sign out
        </Button>
      )}
    </li>
  );
}

function SessionsCard() {
  const sessions = useMySessions();
  const revokeOthers = useRevokeOtherSessions();
  const confirm = useConfirm();
  const others = sessions.data?.filter((s) => !s.current).length ?? 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Where you're signed in</CardTitle>
        <CardDescription>Sessions last 12 hours. End any you don't recognise.</CardDescription>
      </CardHeader>
      <CardContent className="px-0">
        {sessions.isLoading ? (
          <Skeleton className="mx-5 h-20" />
        ) : (
          <ul className="divide-y divide-[color:var(--border)] border-y border-[color:var(--border)]">
            {sessions.data?.map((s) => <SessionRow key={s.id} session={s} />)}
          </ul>
        )}
        {others > 0 && (
          <div className="px-5 pt-4">
            <Button
              variant="outline"
              disabled={revokeOthers.isPending}
              onClick={async () => {
                const ok = await confirm({
                  title: "Sign out everywhere else?",
                  description: `Ends ${others} other session${others === 1 ? "" : "s"}. This one stays signed in.`,
                  confirmLabel: "Sign out others",
                  destructive: true,
                });
                if (!ok) return;
                const { ended } = await revokeOthers.mutateAsync(undefined);
                toast({ title: `${ended} session${ended === 1 ? "" : "s"} ended` });
              }}
            >
              <LogOut data-icon="inline-start" />
              Sign out everywhere else
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/** The signed in admin's own password, authenticator and sessions. */
export default function ConsoleAccountPage() {
  const { admin } = usePlatformAuth();
  return (
    <div className="space-y-8">
      <PageHeader
        section="Console"
        title="Your account"
        description={admin ? `${admin.email} · ${PLATFORM_ROLE_LABELS[admin.role]}` : undefined}
      />
      <div className="grid gap-6 xl:grid-cols-2">
        <PasswordCard />
        <AuthenticatorCard />
      </div>
      <SessionsCard />
    </div>
  );
}
