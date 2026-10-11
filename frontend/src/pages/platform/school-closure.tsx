import { useState, type FormEvent } from "react";
import { type SchoolRow, useDeleteSchool, useSuspendSchool } from "@/api/platform";
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
import { Label } from "@/components/ui/label";
import { toast } from "@/lib/use-toast";
import { extractErrorEnvelope } from "@/lib/api";

const TEXTAREA =
  "flex min-h-[72px] w-full border border-transparent border-b-input bg-transparent px-0 py-2 text-base outline-none transition-[color,border-color] placeholder:text-muted-foreground focus-visible:border-b-ring aria-invalid:border-b-destructive md:text-sm";

type School = Pick<SchoolRow, "id" | "name" | "slug">;

interface DialogProps {
  school: School;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Suspend with a reason. The reason stays in the console; the school sees a fixed message. */
export function SuspendSchoolDialog({ school, open, onOpenChange }: DialogProps) {
  const suspend = useSuspendSchool();
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const close = (next: boolean) => {
    if (!next) {
      setReason("");
      setError(null);
    }
    onOpenChange(next);
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!reason.trim()) {
      setError("Give a reason. Only the Ordo team sees it.");
      return;
    }
    setError(null);
    try {
      await suspend.mutateAsync({ id: school.id, reason: reason.trim() });
      toast({ title: `${school.name} is suspended` });
      close(false);
    } catch (err) {
      const envelope = extractErrorEnvelope(err);
      setError(envelope.errors?.reason?.join(" ") ?? envelope.detail);
    }
  };

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Suspend {school.name}?</DialogTitle>
          <DialogDescription>
            Its users are signed out of every page until you reactivate it. No data is touched, and
            a job already running still finishes.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="suspend-reason">Reason</Label>
            <textarea
              id="suspend-reason"
              rows={3}
              autoFocus
              className={TEXTAREA}
              placeholder="Only the Ordo team sees this."
              value={reason}
              aria-invalid={error ? true : undefined}
              onChange={(e) => setReason(e.target.value)}
            />
            {error && <p className="text-[13px] text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => close(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" disabled={suspend.isPending}>
              {suspend.isPending ? "Suspending…" : "Suspend school"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/** Delete after typing the slug. Purged for good 30 days later unless restored. */
export function DeleteSchoolDialog({ school, open, onOpenChange }: DialogProps) {
  const remove = useDeleteSchool();
  const [typed, setTyped] = useState("");
  const [error, setError] = useState<string | null>(null);
  const matches = typed.trim() === school.slug;

  const close = (next: boolean) => {
    if (!next) {
      setTyped("");
      setError(null);
    }
    onOpenChange(next);
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!matches) return;
    setError(null);
    try {
      await remove.mutateAsync({ id: school.id, confirm_slug: typed.trim() });
      toast({
        title: `${school.name} is pending deletion`,
        description: "You can restore it for the next 30 days.",
      });
      close(false);
    } catch (err) {
      const envelope = extractErrorEnvelope(err);
      setError(envelope.errors?.confirm_slug?.join(" ") ?? envelope.detail);
    }
  };

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete {school.name}?</DialogTitle>
          <DialogDescription>
            Its users are blocked at once and a final backup is taken. After 30 days the school's
            data, files and address are removed for good. Until then you can restore it.
          </DialogDescription>
        </DialogHeader>
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="delete-confirm">
              Type <span className="font-mono">{school.slug}</span> to confirm
            </Label>
            <Input
              id="delete-confirm"
              autoFocus
              autoComplete="off"
              spellCheck={false}
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => close(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" disabled={!matches || remove.isPending}>
              {remove.isPending ? "Deleting…" : "Delete school"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
