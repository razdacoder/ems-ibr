import type { ReactNode } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { extractErrorEnvelope } from "@/lib/api";

interface Props {
  title: string;
  description?: string;
  toolbar?: ReactNode;
  query?: string;
  onQueryChange?: (q: string) => void;
  searchPlaceholder?: string;
  isLoading: boolean;
  error: unknown;
  isEmpty: boolean;
  emptyMessage?: string;
  children: ReactNode;
  pagination?: ReactNode;
  filters?: ReactNode;
}

export function ListShell({
  title,
  description,
  toolbar,
  query,
  onQueryChange,
  searchPlaceholder = "Search",
  isLoading,
  error,
  isEmpty,
  emptyMessage = "No records found.",
  children,
  pagination,
  filters,
}: Props) {
  return (
    <div className="space-y-10">
      {/* Page header */}
      <header className="flex flex-col gap-6 border-b border-[color:var(--border)] pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            § Catalog · {title}
          </p>
          <h1 className="mt-3 font-serif text-[2.5rem] leading-[1.05] tracking-[-0.015em] sm:text-[3rem]">
            {title}.
          </h1>
          {description && (
            <p className="mt-3 max-w-2xl text-[14.5px] leading-[1.65] text-muted-foreground">
              {description}
            </p>
          )}
        </div>
        {toolbar && (
          <div className="flex shrink-0 items-center gap-2">{toolbar}</div>
        )}
      </header>

      {/* Toolbar row */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            All {title.toLowerCase()}
          </span>
          {filters}
        </div>
        {onQueryChange && (
          <div className="relative w-full sm:max-w-xs">
            <Search
              className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
              strokeWidth={2}
            />
            <Input
              placeholder={searchPlaceholder}
              className="h-9 pl-9 font-mono text-[12px]"
              value={query ?? ""}
              onChange={(e) => onQueryChange(e.target.value)}
            />
          </div>
        )}
      </div>

      {/* Body card */}
      <div className="overflow-hidden rounded-[12px] border border-[color:var(--border)] bg-card">
        {error ? (
          <Alert variant="destructive" className="m-4">
            <AlertDescription>
              {extractErrorEnvelope(error).detail}
            </AlertDescription>
          </Alert>
        ) : null}
        {isLoading ? (
          <div className="space-y-2 p-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : isEmpty ? (
          <div className="grid place-items-center px-6 py-20 text-center">
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
              No records
            </p>
            <p className="mt-3 font-serif text-[1.25rem] italic text-muted-foreground">
              {emptyMessage}
            </p>
          </div>
        ) : (
          children
        )}
        {pagination && (
          <div className="border-t border-[color:var(--border)] bg-[color:var(--muted)]/40 px-4 py-3">
            {pagination}
          </div>
        )}
      </div>
    </div>
  );
}
