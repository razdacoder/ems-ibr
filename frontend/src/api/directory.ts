import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type DirectoryDoc = "hall" | "visa";
export type DirectoryScope = "slot" | "week" | "duration";
export type DirectoryFormat = "pdf" | "docx" | "csv";
export type Period = "AM" | "PM";

export const DIRECTORY_FORMATS: {
  value: DirectoryFormat;
  label: string;
  hint: string;
}[] = [
  { value: "pdf", label: "PDF", hint: "Print-ready, one page per slot" },
  { value: "docx", label: "Word (DOCX)", hint: "Editable, same layout as PDF" },
  { value: "csv", label: "CSV", hint: "Plain data for Excel, without branding" },
];

export interface HallRow {
  hall: string;
  class_name: string;
  count: number;
  matric_range: string;
}

export interface VisaGroup {
  department: string;
  department_name: string;
  codes: string[];
}

export interface DirectorySlot {
  date: string;
  period: Period;
  title: string;
  rows?: HallRow[];
  codes?: string[];
  groups?: VisaGroup[];
}

export interface DirectoryPreview {
  doc: DirectoryDoc;
  scope: DirectoryScope;
  slots: DirectorySlot[];
}

export interface DirectoryParams {
  doc: DirectoryDoc;
  scope: DirectoryScope;
  date?: string;
  period: Period;
}

/** Params object for the request — drops `date` when it isn't needed. */
export function directoryQuery(params: DirectoryParams) {
  const q: Record<string, string> = {
    doc: params.doc,
    scope: params.scope,
    period: params.period,
  };
  if (params.scope !== "duration" && params.date) q.date = params.date;
  return q;
}

/**
 * Export params — the preview query deliberately excludes the format so that
 * switching download format does not invalidate the cached preview.
 *
 * Sent as `fmt`, not `format`: DRF reserves `format` for renderer negotiation,
 * and `?format=pdf` 404s before the view runs.
 */
export function directoryExportQuery(
  params: DirectoryParams & { format: DirectoryFormat },
) {
  return { ...directoryQuery(params), fmt: params.format };
}

export function useDirectoryPreview(params: DirectoryParams, enabled: boolean) {
  return useQuery({
    queryKey: ["directory", "preview", directoryQuery(params)],
    queryFn: async () => {
      const res = await api.get<DirectoryPreview>("/directory/preview/", {
        params: directoryQuery(params),
      });
      return res.data;
    },
    enabled,
  });
}
