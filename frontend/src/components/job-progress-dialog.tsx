import { useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useJobProgress } from "@/api/jobs";

interface Props {
  jobId: string | null;
  title: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (result: Record<string, unknown> | null) => void;
}

export function JobProgressDialog({
  jobId,
  title,
  open,
  onOpenChange,
  onSuccess,
}: Props) {
  const event = useJobProgress(open ? jobId : null);

  useEffect(() => {
    if (!event) return;
    if (event.status === "success") onSuccess?.(event.result);
  }, [event, onSuccess]);

  const status = event?.status ?? "pending";
  const progress = event?.progress ?? 0;
  const isTerminal = status === "success" || status === "failed";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            Progress updates stream over a live WebSocket. Closing this dialog
            does not cancel the job.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Badge variant={statusVariant(status)}>{status}</Badge>
            <span className="text-sm text-muted-foreground">{progress}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>

          {status === "failed" && event?.error_message && (
            <Alert variant="destructive">
              <AlertTitle>Job failed</AlertTitle>
              <AlertDescription>{event.error_message}</AlertDescription>
            </Alert>
          )}
          {status === "success" && (
            <Alert>
              <AlertTitle>Job completed</AlertTitle>
              <AlertDescription>
                {(event?.result as { message?: string } | null)?.message ??
                  "Generation completed."}
              </AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button
            variant={isTerminal ? "default" : "outline"}
            onClick={() => onOpenChange(false)}
          >
            {isTerminal ? "Close" : "Hide"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function statusVariant(s: string) {
  if (s === "success") return "default" as const;
  if (s === "failed") return "destructive" as const;
  if (s === "running") return "secondary" as const;
  return "outline" as const;
}
