import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getToken, wsUrl } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { toast } from "@/lib/use-toast";
import type { PaginatedResponse } from "./types";

export type NotificationKind =
  | "timetable_published"
  | "timetable_withdrawn"
  | "general";

export interface AppNotification {
  id: number;
  kind: NotificationKind;
  title: string;
  body: string;
  /** In-app route the notification opens, e.g. "/timetable". */
  link: string;
  data: Record<string, unknown>;
  created_at: string;
  read_at: string | null;
}

type StreamEvent =
  | { type: "unread"; count: number }
  | { type: "notification"; notification: AppNotification };

const KEY = ["notifications"] as const;
const COUNT_KEY = [...KEY, "unread-count"] as const;

export function useNotifications(enabled = true) {
  return useQuery({
    queryKey: [...KEY, "list"],
    queryFn: async () => {
      const res = await api.get<PaginatedResponse<AppNotification>>(
        "/notifications/",
        { params: { page_size: 20 } },
      );
      return res.data;
    },
    enabled,
  });
}

export function useUnreadCount() {
  const auth = useAuth();
  return useQuery({
    queryKey: COUNT_KEY,
    queryFn: async () => {
      const res = await api.get<{ count: number }>(
        "/notifications/unread-count/",
      );
      return res.data.count;
    },
    enabled: auth.status === "authenticated",
    // The socket keeps this fresh; polling only covers a socket that is down.
    refetchInterval: 60_000,
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.post(`/notifications/${id}/read/`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.post("/notifications/read-all/");
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

/** Keep the inbox live over WebSocket while signed in: a new notification
 *  bumps the unread count, refreshes the list, shows a toast, and (for a
 *  timetable change) refreshes the timetable. Reconnects with backoff; the
 *  unread-count poll covers the gaps. Mount once, in the app shell. */
export function useNotificationStream() {
  const auth = useAuth();
  const qc = useQueryClient();

  useEffect(() => {
    if (auth.status !== "authenticated") return;
    let ws: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let attempts = 0;
    let closed = false;

    const connect = () => {
      const token = getToken();
      if (!token || closed) return;
      ws = new WebSocket(wsUrl(`/ws/notifications/?token=${token}`));
      ws.onopen = () => {
        attempts = 0;
      };
      ws.onmessage = (msg) => {
        let event: StreamEvent;
        try {
          event = JSON.parse(msg.data) as StreamEvent;
        } catch {
          return;
        }
        if (event.type === "unread") {
          qc.setQueryData(COUNT_KEY, event.count);
          return;
        }
        const n = event.notification;
        qc.setQueryData<number>(COUNT_KEY, (c) => (c ?? 0) + 1);
        qc.invalidateQueries({ queryKey: [...KEY, "list"] });
        if (n.kind === "timetable_published" || n.kind === "timetable_withdrawn") {
          qc.invalidateQueries({ queryKey: ["timetable"] });
        }
        toast({ title: n.title, description: n.body || undefined });
      };
      ws.onclose = (e) => {
        ws = null;
        // 4401: the token is no good, so retrying will not help.
        if (closed || e.code === 4401) return;
        const delay = Math.min(30_000, 1_000 * 2 ** attempts++);
        retry = setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      if (ws && ws.readyState <= WebSocket.OPEN) ws.close();
    };
  }, [auth.status, qc]);
}
