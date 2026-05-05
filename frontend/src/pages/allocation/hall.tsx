import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useHallAllocation } from "@/api/scheduling";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";
import { useQueryClient } from "@tanstack/react-query";

export default function HallAllocationPage() {
  const [params] = useSearchParams();
  const date = params.get("date") ?? undefined;
  const period = (params.get("period") ?? "AM") as "AM" | "PM";
  const hallId = params.get("hall_id");
  const { user } = useAuth();
  const isAdmin = !!user?.is_staff;
  const qc = useQueryClient();

  const data = useHallAllocation({
    date,
    period,
    hall_id: hallId ? Number(hallId) : undefined,
  });
  const [seatInputs, setSeatInputs] = useState<Record<number, string>>({});

  const onAssign = async (saId: number) => {
    const seat = seatInputs[saId];
    if (!seat) return;
    try {
      await api.post("/allocation/manual-assign/", {
        seat_arrangement_id: saId,
        seat_number: Number(seat),
      });
      toast({ title: "Seat assigned" });
      setSeatInputs((s) => ({ ...s, [saId]: "" }));
      qc.invalidateQueries({ queryKey: ["allocation"] });
    } catch (err) {
      toast({
        title: "Assign failed",
        description: extractErrorEnvelope(err).detail,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-10">
      <Link
        to={`/allocation?date=${date}&period=${period}`}
        className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-3" strokeWidth={2.25} />
        Back to allocation
      </Link>

      {data.isLoading ? (
        <Skeleton className="h-32" />
      ) : data.error ? (
        <Alert variant="destructive">
          <AlertDescription>
            {extractErrorEnvelope(data.error).detail}
          </AlertDescription>
        </Alert>
      ) : data.data ? (
        <>
          <header className="flex flex-col gap-6 border-b border-[color:var(--border)] pb-8 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                § Allocation · Hall
              </p>
              <h1 className="mt-3 font-serif text-[2.5rem] leading-[1.05] tracking-[-0.015em] sm:text-[3rem]">
                {data.data.hall.name}.
              </h1>
              <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                {data.data.date} · {data.data.period} · {data.data.hall.rows} ×{" "}
                {data.data.hall.columns} grid · cap {data.data.hall.capacity}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-6 self-start sm:self-end">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                  Placed
                </p>
                <p className="mt-1 font-serif text-[2rem] tabular-nums text-[color:var(--accent-green-fg)]">
                  {data.data.placed.length}
                </p>
              </div>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                  Unplaced
                </p>
                <p className="mt-1 font-serif text-[2rem] tabular-nums text-[color:var(--accent-red-fg)]">
                  {data.data.unplaced.length}
                </p>
              </div>
            </div>
          </header>

          <Tabs defaultValue="placed">
            <TabsList>
              <TabsTrigger value="placed">
                Placed ({data.data.placed.length})
              </TabsTrigger>
              <TabsTrigger value="unplaced">
                Unplaced ({data.data.unplaced.length})
              </TabsTrigger>
            </TabsList>
            <TabsContent value="placed">
              <Card>
                <CardContent className="pt-6">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[80px]">Seat</TableHead>
                        <TableHead className="w-[180px]">Matric no.</TableHead>
                        <TableHead>Student</TableHead>
                        <TableHead className="w-[120px]">Course</TableHead>
                        <TableHead className="w-[160px]">Class</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.data.placed.length === 0 ? (
                        <TableRow>
                          <TableCell
                            colSpan={5}
                            className="py-12 text-center font-serif italic text-muted-foreground"
                          >
                            Nobody seated yet.
                          </TableCell>
                        </TableRow>
                      ) : (
                        data.data.placed
                          .sort(
                            (a, b) =>
                              (a.seat_number ?? 0) - (b.seat_number ?? 0),
                          )
                          .map((row) => (
                            <TableRow key={row.id}>
                              <TableCell>
                                <kbd className="rounded-[4px] border border-[color:var(--border)] bg-[color:var(--muted)] px-2 py-0.5 font-mono text-[11px] tabular-nums">
                                  #{row.seat_number}
                                </kbd>
                              </TableCell>
                              <TableCell>
                                <span className="font-mono text-[12px] tracking-wide">
                                  {row.student?.matric_no}
                                </span>
                              </TableCell>
                              <TableCell className="font-serif text-[1rem] tracking-[-0.005em]">
                                {row.student?.first_name} {row.student?.last_name}
                              </TableCell>
                              <TableCell>
                                <span className="font-mono text-[12px] tracking-wide">
                                  {row.course.code}
                                </span>
                              </TableCell>
                              <TableCell className="text-muted-foreground">
                                {row.class.name}
                              </TableCell>
                            </TableRow>
                          ))
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="unplaced">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Unplaced students</CardTitle>
                  <CardDescription>
                    {isAdmin
                      ? "Type a seat number and click Assign to place a student manually."
                      : "Only admins can place students manually."}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[180px]">Matric no.</TableHead>
                        <TableHead>Student</TableHead>
                        <TableHead className="w-[120px]">Course</TableHead>
                        <TableHead className="w-[160px]">Class</TableHead>
                        {isAdmin && (
                          <TableHead className="w-[260px]">Manual seat</TableHead>
                        )}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.data.unplaced.length === 0 ? (
                        <TableRow>
                          <TableCell
                            colSpan={isAdmin ? 5 : 4}
                            className="py-12 text-center font-serif italic text-[color:var(--accent-green-fg)]"
                          >
                            Everyone is seated.
                          </TableCell>
                        </TableRow>
                      ) : (
                        data.data.unplaced.map((row) => (
                          <TableRow key={row.id}>
                            <TableCell>
                              <span className="font-mono text-[12px] tracking-wide">
                                {row.student?.matric_no}
                              </span>
                            </TableCell>
                            <TableCell className="font-serif text-[1rem] tracking-[-0.005em]">
                              {row.student?.first_name} {row.student?.last_name}
                            </TableCell>
                            <TableCell>
                              <span className="font-mono text-[12px] tracking-wide">
                                {row.course.code}
                              </span>
                            </TableCell>
                            <TableCell className="text-muted-foreground">
                              {row.class.name}
                            </TableCell>
                            {isAdmin && (
                              <TableCell>
                                <div className="flex gap-2">
                                  <Input
                                    type="number"
                                    min={1}
                                    max={
                                      data.data?.hall.rows *
                                      data.data?.hall.columns
                                    }
                                    placeholder="Seat #"
                                    value={seatInputs[row.id] ?? ""}
                                    onChange={(e) =>
                                      setSeatInputs((s) => ({
                                        ...s,
                                        [row.id]: e.target.value,
                                      }))
                                    }
                                    className="h-8 w-24 font-mono text-[12px]"
                                  />
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => onAssign(row.id)}
                                    disabled={!seatInputs[row.id]}
                                  >
                                    Assign
                                  </Button>
                                </div>
                              </TableCell>
                            )}
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      ) : null}
    </div>
  );
}
