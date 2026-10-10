import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowLeft, Loader2, Pencil, RotateCcw, Send } from "lucide-react";
import { FEATURE_LABELS, type SchoolDetail, useSchool } from "@/api/platform";
import { PageHeader } from "@/components/layout/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { extractErrorEnvelope } from "@/lib/api";
import { orEmpty } from "@/lib/format";
import { isPlatformOwner, usePlatformAuth } from "@/lib/platform-auth";
import { SchoolStatusBadge, formatDay, useSchoolActions } from "./schools";

function BackToSchools() {
  return (
    <Link
      to="/console"
      className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground hover:text-foreground"
    >
      <ArrowLeft className="size-3.5" aria-hidden />
      Schools
    </Link>
  );
}

export default function ConsoleSchoolDetailPage({ id }: { id: number }) {
  const school = useSchool(id);

  if (school.isLoading) {
    return (
      <div className="space-y-8">
        <BackToSchools />
        <Skeleton className="h-12 w-2/3" />
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      </div>
    );
  }
  if (school.error || !school.data) {
    return (
      <div className="space-y-8">
        <BackToSchools />
        <Alert variant="destructive">
          <AlertDescription>{extractErrorEnvelope(school.error).detail}</AlertDescription>
        </Alert>
      </div>
    );
  }
  return <SchoolView school={school.data} />;
}

function SchoolView({ school }: { school: SchoolDetail }) {
  const { admin } = usePlatformAuth();
  const actions = useSchoolActions();
  const owner = isPlatformOwner(admin);
  const firstAdmin = school.first_admin;
  const canResend = school.status === "active" && firstAdmin !== null && !firstAdmin.joined;
  const features = school.features_override;

  return (
    <div className="space-y-8">
      <BackToSchools />
      <PageHeader
        section="Console · School"
        title={school.name}
        description={school.domain ?? school.slug}
        meta={<SchoolStatusBadge status={school.status} />}
        actions={
          <>
            {owner && school.status === "failed" && (
              <Button variant="brand" disabled={actions.pending} onClick={() => void actions.retry(school)}>
                <RotateCcw data-icon="inline-start" />
                Retry setup
              </Button>
            )}
            {owner && (
              <Link
                to="/console/schools/$id/edit"
                params={{ id: String(school.id) }}
                className={buttonVariants({ variant: "outline" })}
              >
                <Pencil data-icon="inline-start" />
                Edit
              </Link>
            )}
            {canResend && (
              <Button variant="outline" disabled={actions.pending} onClick={() => void actions.resend(school)}>
                <Send data-icon="inline-start" />
                Resend invite
              </Button>
            )}
          </>
        }
      />

      {school.status === "provisioning" && (
        <Alert>
          <Loader2 className="animate-spin" aria-hidden />
          <AlertTitle>Setting up</AlertTitle>
          <AlertDescription>
            Ordo is creating this school's database and emailing {school.first_admin_email} an
            invite. This page updates on its own when it's done.
          </AlertDescription>
        </Alert>
      )}
      {school.status === "failed" && (
        <Alert variant="destructive">
          <AlertTitle>Setup failed</AlertTitle>
          <AlertDescription>
            <p>
              {owner
                ? "Retry drops whatever was half built and starts again from an empty database."
                : "Ask an Owner to retry the setup."}
            </p>
            {school.provisioning_error && (
              <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap break-words bg-[color:var(--destructive)]/5 p-3 font-mono text-[12px]">
                {school.provisioning_error}
              </pre>
            )}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <Section title="First administrator">
          <Row label="Name">{school.first_admin_name}</Row>
          <Row label="Email">{school.first_admin_email}</Row>
          <Row label="Status">
            {firstAdmin === null ? (
              <span className="text-muted-foreground">Invited once setup finishes</span>
            ) : firstAdmin.joined ? (
              <Badge>Joined</Badge>
            ) : firstAdmin.invite_expires_at &&
              new Date(firstAdmin.invite_expires_at) > new Date() ? (
              <span>Invite open until {formatDay(firstAdmin.invite_expires_at)}</span>
            ) : (
              <Badge variant="warning">Invite expired, resend it</Badge>
            )}
          </Row>
        </Section>

        <Section title="Plan">
          <Row label="Plan">{school.plan.name}</Row>
          <Row label="Student limit">
            {school.max_students_override ?? <span className="text-muted-foreground">Plan's limit</span>}
          </Row>
          <Row label="Staff limit">
            {school.max_staff_users_override ?? <span className="text-muted-foreground">Plan's limit</span>}
          </Row>
          <Row label="Features">
            {features === null ? (
              <span className="text-muted-foreground">Plan's features</span>
            ) : features.length ? (
              features.map((f) => FEATURE_LABELS[f]).join(", ")
            ) : (
              "None"
            )}
          </Row>
          <Row label="Started">{formatDay(school.plan_started_on)}</Row>
          <Row label="Renews">{formatDay(school.renews_on)}</Row>
        </Section>

        <Section title="School">
          <Row label="Address">
            {school.domains.map((d) => (
              <span key={d.domain} className="block font-mono text-[12.5px]">
                {d.domain}
              </span>
            ))}
          </Row>
          <Row label="Time zone">{school.timezone}</Row>
          <Row label="Country">{orEmpty(school.country)}</Row>
          <Row label="Created">
            {formatDay(school.created_at)}
            {school.created_by && (
              <span className="text-muted-foreground"> by {school.created_by.name}</span>
            )}
          </Row>
        </Section>

        <Section title="Contact">
          <Row label="Name">{orEmpty(school.contact_name)}</Row>
          <Row label="Email">{orEmpty(school.contact_email)}</Row>
          <Row label="Notes">
            {school.notes ? (
              <span className="whitespace-pre-wrap">{school.notes}</span>
            ) : (
              <span className="text-muted-foreground">None</span>
            )}
          </Row>
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="divide-y divide-[color:var(--border)]">{children}</dl>
      </CardContent>
    </Card>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[120px_1fr] gap-4 py-2.5 text-[14px]">
      <dt className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-muted-foreground pt-0.5">
        {label}
      </dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  );
}
