import type { ReactNode } from "react";
import { Search } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
    <div className="space-y-6">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-semibold">{title}</h1>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        {toolbar}
      </div>
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0 gap-3">
          <CardTitle className="text-base">All {title.toLowerCase()}</CardTitle>
          <div className="flex items-center gap-2">
            {filters}
            {onQueryChange && (
              <div className="relative w-full max-w-xs">
                <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder={searchPlaceholder}
                  className="pl-8"
                  value={query ?? ""}
                  onChange={(e) => onQueryChange(e.target.value)}
                />
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {error ? (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>
                {extractErrorEnvelope(error).detail}
              </AlertDescription>
            </Alert>
          ) : null}
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : isEmpty ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              {emptyMessage}
            </p>
          ) : (
            children
          )}
          {pagination}
        </CardContent>
      </Card>
    </div>
  );
}
