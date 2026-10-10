import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, CheckCheck } from "lucide-react";
import {
  useMarkAllRead,
  useMarkRead,
  useNotifications,
  useUnreadCount,
  type AppNotification,
} from "@/api/notifications";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

function timeAgo(iso: string): string {
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

/** Inbox bell: unread badge and the latest notifications. ``label`` shows
 *  the word beside the icon (the expanded sidebar). */
export function NotificationBell({
  label = false,
  side = "bottom",
  align = "end",
  className,
}: {
  label?: boolean;
  side?: "top" | "bottom" | "right";
  align?: "start" | "end";
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const unread = useUnreadCount().data ?? 0;
  const list = useNotifications(open);
  const markRead = useMarkRead();
  const markAll = useMarkAllRead();
  const items = list.data?.results ?? [];

  const openItem = (n: AppNotification) => {
    if (!n.read_at) markRead.mutate(n.id);
    if (n.link) navigate(n.link);
  };

  const badge = unread > 99 ? "99+" : String(unread);

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger
        aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
        title="Notifications"
        className={cn(
          "relative inline-flex items-center rounded-md text-muted-foreground transition-colors hover:bg-[color:var(--brand-soft)]/40 hover:text-foreground focus:outline-none focus-visible:ring-1 focus-visible:ring-[color:var(--brand)]/40",
          label ? "w-full gap-2.5 px-2.5 py-1.5 text-[13.5px]" : "size-8 justify-center",
          className,
        )}
      >
        <span className="relative inline-flex">
          <Bell className="size-3.5 shrink-0" strokeWidth={2} />
          {unread > 0 && (
            <span
              aria-hidden
              className="absolute -right-2 -top-2 grid h-3.5 min-w-3.5 place-items-center rounded-full px-1 font-mono text-[9px] font-semibold leading-none"
              style={{
                backgroundColor: "var(--brand)",
                color: "var(--brand-foreground)",
              }}
            >
              {badge}
            </span>
          )}
        </span>
        {label && <span className="font-medium">Notifications</span>}
      </DropdownMenuTrigger>
      <DropdownMenuContent
        side={side}
        align={align}
        sideOffset={8}
        className="w-[min(360px,calc(100vw-32px))] p-0"
      >
        <div className="flex items-center justify-between border-b border-[color:var(--border)] px-3 py-2.5">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            Notifications
          </p>
          <button
            type="button"
            disabled={!unread || markAll.isPending}
            onClick={() => markAll.mutate()}
            className="inline-flex items-center gap-1 text-[12px] text-muted-foreground transition-colors hover:text-foreground disabled:opacity-40"
          >
            <CheckCheck className="size-3.5" strokeWidth={2} />
            Mark all read
          </button>
        </div>
        <div className="max-h-[420px] overflow-y-auto p-1">
          {list.isLoading ? (
            <p className="px-3 py-6 text-center text-[13px] text-muted-foreground">
              Loading…
            </p>
          ) : items.length === 0 ? (
            <p className="px-3 py-8 text-center font-serif italic text-muted-foreground">
              Nothing new.
            </p>
          ) : (
            items.map((n) => (
              <DropdownMenuItem
                key={n.id}
                onClick={() => openItem(n)}
                className="flex items-start gap-2.5 px-2.5 py-2"
              >
                <span
                  aria-hidden
                  className="mt-1.5 size-1.5 shrink-0 rounded-full"
                  style={{
                    backgroundColor: n.read_at ? "transparent" : "var(--brand)",
                  }}
                />
                <span className="min-w-0 flex-1">
                  <span
                    className={cn(
                      "block text-[13px]",
                      n.read_at ? "text-muted-foreground" : "font-medium text-foreground",
                    )}
                  >
                    {n.title}
                  </span>
                  {n.body && (
                    <span className="mt-0.5 block text-[12px] leading-snug text-muted-foreground">
                      {n.body}
                    </span>
                  )}
                  <span className="mt-1 block font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground/80">
                    {timeAgo(n.created_at)}
                  </span>
                </span>
              </DropdownMenuItem>
            ))
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
