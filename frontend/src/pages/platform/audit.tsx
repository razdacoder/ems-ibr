import { useState } from "react";
import { usePlatformAudit } from "@/api/platform";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ListShell } from "@/components/data-table/list-shell";
import { PaginationFooter } from "@/components/data-table/pagination";
import { orEmpty } from "@/lib/format";

/** Readable names for the actions the console records. */
const ACTION_LABELS: Record<string, string> = {
  login: "Signed in",
  logout: "Signed out",
  login_failed: "Wrong password",
  totp_failed: "Wrong code",
  totp_enrolled: "Set up two factor sign in",
  admin_invited: "Invited an admin",
  admin_invite_resent: "Resent an admin invite",
  admin_accepted: "Accepted their invite",
  admin_updated: "Changed an admin",
  admin_2fa_reset: "Reset an admin's two factor sign in",
  unlocked: "Unlocked an admin's sign in",
  school_created: "Created a school",
  school_provisioned: "School set up",
  school_provisioning_failed: "School setup failed",
  school_provisioning_retried: "Retried a school's setup",
  school_invite_resent: "Resent a school's first admin invite",
};

/** Written by background work, not by an admin. */
const SYSTEM_ACTIONS = new Set(["school_provisioned", "school_provisioning_failed"]);

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/** Who an entry is about, when it isn't the admin who acted. */
function subject(detail: Record<string, unknown>): string | null {
  return typeof detail.email === "string" ? detail.email : null;
}

export default function ConsoleAuditPage() {
  const [page, setPage] = useState(1);
  const list = usePlatformAudit({ page });

  return (
    <ListShell
      title="Audit log"
      description="Every console sign in, failed attempt and change, with who did it, when and from where."
      isLoading={list.isLoading}
      error={list.error}
      isEmpty={!list.data?.results.length}
      emptyMessage="Nothing recorded yet."
      pagination={
        list.data && (
          <PaginationFooter page={page} pageSize={15} total={list.data.count} onPageChange={setPage} />
        )
      }
    >
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[180px]">When</TableHead>
            <TableHead>Admin</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>School</TableHead>
            <TableHead className="w-[140px]">IP</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {list.data?.results.map((row) => {
            const about = subject(row.detail);
            return (
              <TableRow key={row.id}>
                <TableCell className="whitespace-nowrap font-mono text-[12px] text-muted-foreground">
                  {formatTimestamp(row.created_at)}
                </TableCell>
                <TableCell>
                  <span className="block font-medium">
                    {row.admin?.name ?? (SYSTEM_ACTIONS.has(row.action) ? "Ordo" : "Unknown")}
                  </span>
                  {row.admin && (
                    <span className="block text-[12px] text-muted-foreground">{row.admin.email}</span>
                  )}
                </TableCell>
                <TableCell>
                  <span className="block">{ACTION_LABELS[row.action] ?? row.action}</span>
                  {about && about !== row.admin?.email && (
                    <span className="block font-mono text-[11px] text-muted-foreground">{about}</span>
                  )}
                </TableCell>
                <TableCell>{orEmpty(row.school?.name)}</TableCell>
                <TableCell className="font-mono text-[12px] text-muted-foreground">
                  {orEmpty(row.ip)}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </ListShell>
  );
}
