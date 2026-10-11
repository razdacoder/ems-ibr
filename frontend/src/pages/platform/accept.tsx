import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useSearch } from "@tanstack/react-router";
import { AxiosError } from "axios";
import { ArrowRight } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { PasswordInput } from "@/components/ui/password-input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { acceptAdminInvite } from "@/api/platform";
import { extractErrorEnvelope } from "@/lib/api";
import { ConsoleAuthFrame } from "./auth-frame";

const LABEL =
  "font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground";

const schema = z
  .object({
    password: z.string().min(8, "Use at least 8 characters"),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, {
    path: ["confirm"],
    message: "The passwords don't match",
  });

type State = "form" | "done" | "gone";

/** Set a password from a platform admin invite link (valid once, for 48 hours). */
export default function AcceptAdminInvitePage() {
  const { token } = useSearch({ from: "/_platform/accept" });
  const [state, setState] = useState<State>(token ? "form" : "gone");
  const [error, setError] = useState<string | null>(null);
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { password: "", confirm: "" },
  });

  const onSubmit = async (values: z.infer<typeof schema>) => {
    setError(null);
    try {
      await acceptAdminInvite(token ?? "", values.password);
      setState("done");
    } catch (err) {
      if (err instanceof AxiosError && err.response?.status === 410) {
        setState("gone");
        return;
      }
      const envelope = extractErrorEnvelope(err);
      const passwordErrors = envelope.errors?.password;
      if (passwordErrors) {
        form.setError("password", { message: passwordErrors.join(" ") });
      } else {
        setError(envelope.detail);
      }
    }
  };

  if (state === "done") {
    return (
      <ConsoleAuthFrame
        eyebrow="Invite accepted"
        title="Your password is set."
        description="Sign in now. You'll be asked to set up an authenticator app the first time."
      >
        <Link to="/console/login" className={buttonVariants({ variant: "brand", size: "lg", className: "w-full" })}>
          Sign in
          <ArrowRight data-icon="inline-end" strokeWidth={2.25} />
        </Link>
      </ConsoleAuthFrame>
    );
  }

  if (state === "gone") {
    return (
      <ConsoleAuthFrame
        eyebrow="Invite"
        title="This link no longer works."
        description="Invite links work once and expire after 48 hours. Ask an Owner to resend your invite."
      >
        <Link to="/console/login" className={buttonVariants({ variant: "outline", className: "w-full" })}>
          Go to sign in
        </Link>
      </ConsoleAuthFrame>
    );
  }

  return (
    <ConsoleAuthFrame
      eyebrow="You're invited"
      title="Set your password."
      description="You've been invited to the Ordo platform console. Choose a password to finish setting up your account."
    >
      {error && (
        <Alert variant="destructive" className="mb-6" role="alert">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5" noValidate>
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel className={LABEL}>New password</FormLabel>
                <FormControl>
                  <PasswordInput autoComplete="new-password" autoFocus className="h-11" {...field} />
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
          <Button
            type="submit"
            variant="brand"
            size="lg"
            className="w-full"
            disabled={form.formState.isSubmitting}
          >
            {form.formState.isSubmitting ? "Saving…" : "Set password"}
          </Button>
        </form>
      </Form>
    </ConsoleAuthFrame>
  );
}
