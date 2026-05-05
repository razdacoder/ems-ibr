import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { useTimetableDates } from "@/api/scheduling";
import { useHalls } from "@/api/halls";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
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
import { downloadAuthenticatedFile } from "@/lib/download";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";
import { PageHeader } from "@/components/layout/page-header";

export default function ExportsPage() {
  const dates = useTimetableDates();
  const halls = useHalls({ page: 1 });
  const [date, setDate] = useState<string | undefined>();
  const [period, setPeriod] = useState<"AM" | "PM">("AM");
  const [hallId, setHallId] = useState<string | undefined>();

  useEffect(() => {
    if (!date && dates.data?.dates.length) setDate(dates.data.dates[0]);
  }, [date, dates.data]);

  const tryDownload = async (url: string, fallback: string, params?: Record<string, string | number | undefined>) => {
    try {
      await downloadAuthenticatedFile(url, fallback, params);
      toast({ title: "Download started" });
    } catch (err) {
      toast({
        title: "Download failed",
        description: extractErrorEnvelope(err).detail,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-10">
      <PageHeader
        section="Operations · Exports"
        title="Exports."
        description="Download CSV, Excel, and Word reports. Slot-scoped exports use the selected date and period."
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Slot</CardTitle>
          <CardDescription>
            Used by distribution, arrangement, and attendance-sheet exports.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-2">
          <Select
            value={date ?? ""}
            onValueChange={(v) => setDate(v ?? undefined)}
            disabled={!dates.data?.dates.length}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Pick a date" />
            </SelectTrigger>
            <SelectContent>
              {dates.data?.dates.map((d) => (
                <SelectItem key={d} value={d}>
                  {d}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={period}
            onValueChange={(v) => setPeriod(v as "AM" | "PM")}
          >
            <SelectTrigger className="w-[120px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="AM">AM</SelectItem>
              <SelectItem value="PM">PM</SelectItem>
            </SelectContent>
          </Select>
          <Select value={hallId ?? ""} onValueChange={(v) => setHallId(v ?? undefined)}>
            <SelectTrigger className="w-[260px]">
              <SelectValue placeholder="Hall (for attendance sheets)" />
            </SelectTrigger>
            <SelectContent>
              {halls.data?.results.map((h) => (
                <SelectItem key={h.id} value={String(h.id)}>
                  {h.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <ExportCard
          title="Timetable CSV"
          description="Per-department exam schedule as CSV."
          onDownload={() =>
            tryDownload("/exports/timetable/", "timetable.csv")
          }
        />
        <ExportCard
          title="Distribution CSV"
          description="Hall-to-class assignments for the selected slot."
          disabled={!date || !period}
          onDownload={() =>
            tryDownload("/exports/distribution/", `distribution-${date}-${period}.csv`, {
              date,
              period,
            })
          }
        />
        <ExportCard
          title="Arrangement ZIP"
          description="Per-course seat arrangements (CSV bundle)."
          disabled={!date || !period}
          onDownload={() =>
            tryDownload("/exports/arrangement/", `arrangement-${date}-${period}.zip`, {
              date,
              period,
            })
          }
        />
        <ExportCard
          title="Attendance sheets"
          description="DOCX zip with one sheet per course."
          disabled={!date || !period || !hallId}
          onDownload={() =>
            tryDownload(
              "/exports/attendance-sheets/",
              `attendance-${date}-${period}.zip`,
              { date, period, hall_id: hallId },
            )
          }
        />
        <ExportCard
          title="Broadsheet"
          description="Full Excel broadsheet across the entire timetable."
          onDownload={() =>
            tryDownload("/exports/broadsheet/", "broadsheet.xlsx")
          }
        />
      </div>
    </div>
  );
}

function ExportCard({
  title,
  description,
  disabled,
  onDownload,
}: {
  title: string;
  description: string;
  disabled?: boolean;
  onDownload: () => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardFooter>
        <Button onClick={onDownload} disabled={disabled} variant="outline">
          <Download className="mr-2 h-4 w-4" /> Download
        </Button>
      </CardFooter>
    </Card>
  );
}
