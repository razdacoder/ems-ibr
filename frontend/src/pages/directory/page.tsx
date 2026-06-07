import { useEffect, useState } from "react";
import { Download, FileText } from "lucide-react";
import {
  directoryQuery,
  useDirectoryPreview,
  type DirectoryDoc,
  type DirectoryScope,
  type Period,
} from "@/api/directory";
import { useTimetableDates } from "@/api/scheduling";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { PageHeader } from "@/components/layout/page-header";
import { downloadAuthenticatedFile } from "@/lib/download";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";

export default function DirectoryPage() {
  const dates = useTimetableDates();
  const [doc, setDoc] = useState<DirectoryDoc>("hall");
  const [scope, setScope] = useState<DirectoryScope>("slot");
  const [date, setDate] = useState<string | undefined>();
  const [period, setPeriod] = useState<Period>("AM");
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!date && dates.data?.dates.length) setDate(dates.data.dates[0]);
  }, [date, dates.data]);

  const needsDate = scope !== "duration";
  const ready = !needsDate || !!date;
  const preview = useDirectoryPreview({ doc, scope, date, period }, ready);

  const onDownload = async () => {
    setDownloading(true);
    try {
      const label = doc === "hall" ? "hall-directory" : "visa";
      await downloadAuthenticatedFile(
        "/directory/export/",
        `${label}-${scope}.pdf`,
        directoryQuery({ doc, scope, date, period }),
      );
      toast({ title: "PDF download started" });
    } catch (err) {
      toast({
        title: "Export failed",
        description: extractErrorEnvelope(err).detail,
        variant: "destructive",
      });
    } finally {
      setDownloading(false);
    }
  };

  const slots = preview.data?.slots ?? [];

  return (
    <div className="space-y-8">
      <PageHeader
        section="Operations · Documents"
        title="Directory & VISA."
        description="Preview and export the Hall Directory (hall summary) and VISA per slot, week, or the whole exam — as PDF."
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Scope</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <Field label="Document">
            <Select value={doc} onValueChange={(v) => setDoc(v as DirectoryDoc)}>
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="hall">Hall Summary</SelectItem>
                <SelectItem value="visa">VISA</SelectItem>
              </SelectContent>
            </Select>
          </Field>

          <Field label="Range">
            <Select
              value={scope}
              onValueChange={(v) => setScope(v as DirectoryScope)}
            >
              <SelectTrigger className="w-[170px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="slot">Single slot</SelectItem>
                <SelectItem value="week">Week (Mon–Sat)</SelectItem>
                <SelectItem value="duration">Whole exam</SelectItem>
              </SelectContent>
            </Select>
          </Field>

          {needsDate && (
            <Field label="Date">
              <Select
                value={date ?? ""}
                onValueChange={(v) => setDate(v || undefined)}
                disabled={!dates.data?.dates.length}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Pick a date" />
                </SelectTrigger>
                <SelectContent>
                  {dates.data?.dates.map((d) => (
                    <SelectItem key={d} value={d}>
                      {new Date(d).toLocaleDateString(undefined, {
                        weekday: "short",
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                      })}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          )}

          {scope === "slot" && (
            <Field label="Period">
              <Select
                value={period}
                onValueChange={(v) => setPeriod(v as Period)}
              >
                <SelectTrigger className="w-[110px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="AM">AM</SelectItem>
                  <SelectItem value="PM">PM</SelectItem>
                </SelectContent>
              </Select>
            </Field>
          )}

          <Button
            onClick={onDownload}
            disabled={!ready || downloading || preview.isLoading}
            className="ml-auto"
          >
            <Download className="mr-2 h-4 w-4" />
            {downloading ? "Preparing…" : "Download PDF"}
          </Button>
        </CardContent>
      </Card>

      {/* Preview */}
      {!ready ? (
        <Alert>
          <AlertDescription>Pick a date to preview.</AlertDescription>
        </Alert>
      ) : preview.isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : preview.error ? (
        <Alert variant="destructive">
          <AlertDescription>
            {extractErrorEnvelope(preview.error).detail}
          </AlertDescription>
        </Alert>
      ) : slots.length === 0 ? (
        <Alert>
          <AlertDescription>
            No exam slots found for this scope. Generate the timetable
            {doc === "hall" ? " and seat allocation" : ""} first.
          </AlertDescription>
        </Alert>
      ) : (
        <div className="space-y-6">
          {slots.map((slot) => (
            <Card key={`${slot.date}-${slot.period}`}>
              <CardHeader>
                <CardTitle className="text-center font-serif text-[1.1rem] tracking-tight">
                  {slot.title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {doc === "hall" ? (
                  (slot.rows?.length ?? 0) === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No seat allocation generated for this slot.
                    </p>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Hall</TableHead>
                          <TableHead>Class Name</TableHead>
                          <TableHead className="text-center">
                            No. Of Students
                          </TableHead>
                          <TableHead>Matric Numbers</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {slot.rows!.map((r, i) => (
                          <TableRow key={`${r.hall}-${r.class_name}-${i}`}>
                            <TableCell className="font-medium">
                              {r.hall}
                            </TableCell>
                            <TableCell>{r.class_name}</TableCell>
                            <TableCell className="text-center">
                              {r.count}
                            </TableCell>
                            <TableCell className="font-mono text-[13px]">
                              {r.matric_range}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )
                ) : (slot.groups?.length ?? 0) === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No classes scheduled for this slot.
                  </p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[180px]">Department</TableHead>
                        <TableHead>Classes</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {slot.groups!.map((g) => (
                        <TableRow key={g.department}>
                          <TableCell className="align-top font-medium">
                            {g.department}
                            {g.department_name && (
                              <span className="block text-xs font-normal text-muted-foreground">
                                {g.department_name}
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="font-semibold leading-7">
                            {g.codes.join(", ")}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {slots.length === 0 && ready && !preview.isLoading && (
        <p className="flex items-center gap-2 text-xs text-muted-foreground">
          <FileText className="h-3.5 w-3.5" />
          The PDF is generated one page per slot. VISA prints as a single
          block; the preview groups it by department for readability.
        </p>
      )}
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </p>
      {children}
    </div>
  );
}
