import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { AxiosError } from "axios";
import QRCode from "qrcode";
import { ArrowLeft, ArrowRight } from "lucide-react";
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
import { PasswordInput } from "@/components/ui/password-input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { extractErrorEnvelope } from "@/lib/api";
import { usePlatformAuth, type SignInStep } from "@/lib/platform-auth";
import { ConsoleAuthFrame } from "./auth-frame";

const LABEL =
  "font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground";

const passwordSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

const codeSchema = z.object({
  code: z
    .string()
    .trim()
    .regex(/^\d{6}$/, "Enter the 6 digit code from your authenticator app"),
});

/** Where to go after signing in: only console paths, never another site. */
function safeRedirect(back: string | undefined): string {
  return back?.startsWith("/console") ? back : "/console";
}

export default function PlatformLoginPage() {
  const { status } = usePlatformAuth();
  const navigate = useNavigate();
  const search = useSearch({ from: "/_platform/console/login" });
  const [step, setStep] = useState<SignInStep | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (status === "authenticated") {
      navigate({ href: safeRedirect(search.redirect), replace: true });
    }
  }, [status, navigate, search.redirect]);

  const restart = (message: string | null) => {
    setStep(null);
    setNotice(message);
  };

  if (step === null) {
    return (
      <PasswordStep
        notice={notice}
        onNext={(next) => {
          setNotice(null);
          setStep(next);
        }}
      />
    );
  }
  return <CodeStep step={step} onRestart={restart} />;
}

function PasswordStep({
  notice,
  onNext,
}: {
  notice: string | null;
  onNext: (step: SignInStep) => void;
}) {
  const { checkPassword } = usePlatformAuth();
  const [error, setError] = useState<string | null>(null);
  const form = useForm<z.infer<typeof passwordSchema>>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = async (values: z.infer<typeof passwordSchema>) => {
    setError(null);
    try {
      onNext(await checkPassword(values.email, values.password));
    } catch (err) {
      setError(extractErrorEnvelope(err).detail);
    }
  };

  return (
    <ConsoleAuthFrame
      eyebrow="Ordo team"
      title="Sign in."
      description="The platform console is for the Ordo team. School staff sign in at their school's own address."
    >
      {(error ?? notice) && (
        <Alert variant="destructive" className="mb-6" role="alert">
          <AlertDescription>{error ?? notice}</AlertDescription>
        </Alert>
      )}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5" noValidate>
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel className={LABEL}>Email</FormLabel>
                <FormControl>
                  <Input type="email" autoComplete="email" autoFocus className="h-11" {...field} />
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
                <FormLabel className={LABEL}>Password</FormLabel>
                <FormControl>
                  <PasswordInput autoComplete="current-password" className="h-11" {...field} />
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
            {form.formState.isSubmitting ? "Checking…" : "Continue"}
            {!form.formState.isSubmitting && (
              <ArrowRight data-icon="inline-end" strokeWidth={2.25} />
            )}
          </Button>
        </form>
      </Form>
    </ConsoleAuthFrame>
  );
}

function CodeStep({
  step,
  onRestart,
}: {
  step: SignInStep;
  onRestart: (message: string | null) => void;
}) {
  const { confirmCode } = usePlatformAuth();
  const [error, setError] = useState<string | null>(null);
  const form = useForm<z.infer<typeof codeSchema>>({
    resolver: zodResolver(codeSchema),
    defaultValues: { code: "" },
  });
  const enrolling = step.step === "enroll";

  const onSubmit = async (values: z.infer<typeof codeSchema>) => {
    setError(null);
    try {
      // The page redirects once the session is set.
      await confirmCode(step, values.code);
    } catch (err) {
      // 410: the 5 minute sign in window ran out. Start again.
      if (err instanceof AxiosError && err.response?.status === 410) {
        onRestart(extractErrorEnvelope(err).detail);
        return;
      }
      setError(extractErrorEnvelope(err).detail);
      form.reset({ code: "" });
    }
  };

  return (
    <ConsoleAuthFrame
      eyebrow={enrolling ? "Set up two factor sign in" : "Two factor sign in"}
      title={enrolling ? "Add Ordo to your authenticator." : "Enter your code."}
      description={
        enrolling
          ? "Scan the QR code with an authenticator app (Google Authenticator, 1Password, Authy), then enter the 6 digit code it shows."
          : "Open your authenticator app and enter the 6 digit code for Ordo."
      }
    >
      {step.step === "enroll" && <EnrolmentCode uri={step.otpauth_uri} />}
      {error && (
        <Alert variant="destructive" className="mb-6" role="alert">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5" noValidate>
          <FormField
            control={form.control}
            name="code"
            render={({ field }) => (
              <FormItem>
                <FormLabel className={LABEL}>6 digit code</FormLabel>
                <FormControl>
                  <Input
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    autoFocus
                    maxLength={6}
                    className="h-11 font-mono text-[18px] tracking-[0.4em]"
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
            className="w-full"
            disabled={form.formState.isSubmitting}
          >
            {form.formState.isSubmitting
              ? "Checking…"
              : enrolling
                ? "Confirm and sign in"
                : "Sign in"}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="w-full text-muted-foreground"
            onClick={() => onRestart(null)}
          >
            <ArrowLeft data-icon="inline-start" />
            Use a different account
          </Button>
        </form>
      </Form>
    </ConsoleAuthFrame>
  );
}

/** The otpauth URI as a QR code, plus the secret for typing in by hand. */
export function EnrolmentCode({ uri }: { uri: string }) {
  const [src, setSrc] = useState<string | null>(null);
  const secret = new URL(uri).searchParams.get("secret") ?? "";

  useEffect(() => {
    let live = true;
    QRCode.toDataURL(uri, { margin: 1, width: 220 }).then((url) => {
      if (live) setSrc(url);
    });
    return () => {
      live = false;
    };
  }, [uri]);

  return (
    <div className="mb-6 flex flex-col items-center gap-4 rounded-[12px] border border-[color:var(--border)] bg-card p-5">
      <div className="grid size-[220px] place-items-center rounded-md bg-white p-0">
        {src ? (
          <img src={src} width={220} height={220} alt="QR code to add Ordo to your authenticator app" />
        ) : null}
      </div>
      <div className="w-full text-center">
        <p className={LABEL}>Can't scan? Enter this key</p>
        <code className="mt-2 block break-all font-mono text-[13px] tracking-[0.12em] text-foreground select-all">
          {secret.replace(/(.{4})/g, "$1 ").trim()}
        </code>
      </div>
    </div>
  );
}
