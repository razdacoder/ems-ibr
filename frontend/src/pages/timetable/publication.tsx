import { useEffect, useMemo, useState } from "react";
import { BellRing, Megaphone, Undo2, X } from "lucide-react";
import {
  usePublishTimetable,
  useTimetablePublication,
  useUnpublishTimetable,
} from "@/api/scheduling";
import { useUsers, type UserRow } from "@/api/users";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { extractErrorEnvelope } from "@/lib/api";
import { useConfirm } from "@/lib/confirm";
import { formatEmail } from "@/lib/format";
import { toast } from "@/lib/use-toast";

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

/** Draft or published, with the super admin's publish / withdraw actions.
 *  Generation never publishes: department officers see the timetable only
 *  once it is published here. */
export function PublicationPanel() {
  const status = useTimetablePublication();
  const unpublish = useUnpublishTimetable();
  const confirm = useConfirm();
  const [dialog, setDialog] = useState<"publish" | "resend" | null>(null);

  const data = status.data;
  if (!data?.generated) return null;

  const withdraw = async () => {
    const ok = await confirm({
      title: "Withdraw the timetable?",
      description:
        "Department officers stop seeing it at once. Everyone told it was published is told it was withdrawn.",
      confirmLabel: "Withdraw",
      destructive: true,
    });
    if (!ok) return;
    try {
      const out = await unpublish.mutateAsync({});
      toast({
        title: "Timetable withdrawn",
        description: `Back to draft. ${plural(out.notified.users, "user")} notified.`,
      });
    } catch (err) {
      toast({
        title: "Could not withdraw",
        description: extractErrorEnvelope(err).detail,
        variant: "destructive",
      });
    }
  };

  return (
    <>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-3 rounded-md border border-[color:var(--border)] bg-[color:var(--muted)]/30 px-4 py-3">
        <span
          aria-hidden
          className="size-2 shrink-0 rounded-full"
          style={{
            backgroundColor: data.published
              ? "var(--accent-teal-fg)"
              : "var(--accent-amber-fg)",
          }}
        />
        <div className="min-w-0 flex-1">
          <p className="text-[13.5px] font-medium">
            {data.published ? "Published" : "Draft"}
          </p>
          <p className="text-[12.5px] text-muted-foreground">
            {data.published && data.published_at
              ? `Department officers can see it. Published ${new Date(
                  data.published_at,
                ).toLocaleString()}${
                  data.published_by ? ` by ${formatEmail(data.published_by)}` : ""
                }.`
              : "Only the exam committee can see this timetable. Publish it to show it to department officers and notify them."}
          </p>
        </div>
        {data.published ? (
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => setDialog("resend")}>
              <BellRing data-icon="inline-start" strokeWidth={2} />
              Notify again
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={withdraw}
              disabled={unpublish.isPending}
            >
              <Undo2 data-icon="inline-start" strokeWidth={2} />
              Withdraw
            </Button>
          </div>
        ) : (
          <Button size="sm" onClick={() => setDialog("publish")}>
            <Megaphone data-icon="inline-start" strokeWidth={2} />
            Publish timetable
          </Button>
        )}
      </div>
      <PublishDialog
        mode={dialog}
        onOpenChange={(o) => !o && setDialog(null)}
      />
    </>
  );
}

function PublishDialog({
  mode,
  onOpenChange,
}: {
  mode: "publish" | "resend" | null;
  onOpenChange: (open: boolean) => void;
}) {
  const open = mode !== null;
  const status = useTimetablePublication();
  const publish = usePublishTimetable();
  const departments = useMemo(() => status.data?.departments ?? [], [status.data]);

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [users, setUsers] = useState<UserRow[]>([]);
  const [notify, setNotify] = useState(true);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const search = useUsers({ query: query.trim() || undefined });

  useEffect(() => {
    if (!open) return;
    // First publish: every department. Notify again: pick who.
    setSelected(
      mode === "publish" ? new Set(departments.map((d) => d.id)) : new Set(),
    );
    setUsers([]);
    setNotify(true);
    setQuery("");
    setError(null);
  }, [open, mode, departments]);

  const allSelected = departments.length > 0 && selected.size === departments.length;
  const reach = departments
    .filter((d) => selected.has(d.id))
    .reduce((sum, d) => sum + d.users, 0);
  const matches = (search.data?.results ?? [])
    .filter((u) => u.is_active && !users.some((p) => p.id === u.id))
    .slice(0, 6);
  const nobody = notify && selected.size === 0 && users.length === 0;

  const toggle = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const submit = async () => {
    setError(null);
    try {
      const out = await publish.mutateAsync({
        department_ids: [...selected],
        user_ids: users.map((u) => u.id),
        notify,
      });
      toast({
        title: out.already_published ? "Notifications sent" : "Timetable published",
        description: notify
          ? `${plural(out.notified.users, "user")} notified across ${plural(
              out.notified.departments,
              "department",
            )}.`
          : "No one was notified.",
      });
      onOpenChange(false);
    } catch (err) {
      setError(extractErrorEnvelope(err).detail);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>
            {mode === "resend" ? "Notify again" : "Publish timetable"}
          </DialogTitle>
          <DialogDescription>
            {mode === "resend"
              ? "Send the published timetable to the departments or people you pick."
              : "Department officers will see the timetable. Each department you pick is told about its own papers."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <label className="flex items-center justify-between gap-4">
            <span className="text-[13.5px]">Send notifications</span>
            <Switch
              checked={notify}
              onCheckedChange={(v) => setNotify(Boolean(v))}
              disabled={mode === "resend"}
            />
          </label>

          {notify && (
            <>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                    Departments
                  </p>
                  <button
                    type="button"
                    className="text-[12px] text-muted-foreground hover:text-foreground"
                    onClick={() =>
                      setSelected(
                        allSelected ? new Set() : new Set(departments.map((d) => d.id)),
                      )
                    }
                  >
                    {allSelected ? "Clear" : "Select all"}
                  </button>
                </div>
                <div className="max-h-56 divide-y divide-[color:var(--border)]/60 overflow-y-auto rounded-md border border-[color:var(--border)] bg-[color:var(--muted)]/20">
                  {departments.map((d) => (
                    <label
                      key={d.id}
                      className="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm hover:bg-[color:var(--muted)]/50"
                    >
                      <input
                        type="checkbox"
                        className="h-4 w-4 accent-[color:var(--primary)]"
                        checked={selected.has(d.id)}
                        onChange={() => toggle(d.id)}
                      />
                      <span className="font-mono text-[11px] tracking-wide text-muted-foreground">
                        {d.slug}
                      </span>
                      <span className="min-w-0 flex-1 truncate font-serif text-[0.95rem]">
                        {d.name}
                      </span>
                      <span
                        className={
                          d.users
                            ? "font-mono text-[10px] text-muted-foreground"
                            : "font-mono text-[10px] text-[color:var(--accent-amber-fg)]"
                        }
                      >
                        {d.users ? plural(d.users, "user") : "no users"}
                      </span>
                    </label>
                  ))}
                </div>
                <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                  {selected.size} of {departments.length} selected · reaches{" "}
                  {plural(reach, "user")}
                </p>
              </div>

              <div className="space-y-2">
                <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                  Also notify people
                </p>
                {users.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {users.map((u) => (
                      <span
                        key={u.id}
                        className="inline-flex items-center gap-1 rounded-full border border-[color:var(--border)] bg-[color:var(--muted)]/40 py-0.5 pl-2.5 pr-1 text-[12px]"
                      >
                        {formatEmail(u.email)}
                        <button
                          type="button"
                          aria-label={`Remove ${u.email}`}
                          className="grid size-4 place-items-center rounded-full text-muted-foreground hover:bg-[color:var(--muted)] hover:text-foreground"
                          onClick={() => setUsers((prev) => prev.filter((p) => p.id !== u.id))}
                        >
                          <X className="size-3" strokeWidth={2} />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                <Input
                  placeholder="Search by name or email"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                {query.trim() && (
                  <div className="divide-y divide-[color:var(--border)]/60 rounded-md border border-[color:var(--border)]">
                    {matches.length === 0 ? (
                      <p className="px-3 py-2 text-[12.5px] text-muted-foreground">
                        {search.isFetching ? "Searching…" : "No matching users."}
                      </p>
                    ) : (
                      matches.map((u) => (
                        <button
                          key={u.id}
                          type="button"
                          className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-[13px] hover:bg-[color:var(--muted)]/50"
                          onClick={() => {
                            setUsers((prev) => [...prev, u]);
                            setQuery("");
                          }}
                        >
                          <span className="truncate">{formatEmail(u.email)}</span>
                          <span className="shrink-0 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                            {u.department?.slug ?? u.role ?? ""}
                          </span>
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={publish.isPending || nobody}>
            {mode === "resend" ? "Send" : notify ? "Publish and notify" : "Publish"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
