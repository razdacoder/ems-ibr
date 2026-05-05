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
    <div className="space-y-6">
      <Button asChild variant="ghost" size="sm">
        <Link to={`/allocation?date=${date}&period=${period}`}>
          <ArrowLeft className="mr-1 h-4 w-4" /> Back to allocation
        </Link>
      </Button>

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
          <div className="flex items-end justify-between">
            <div>
              <h1 className="text-2xl font-semibold">{data.data.hall.name}</h1>
              <p className="text-sm text-muted-foreground">
                {data.data.date} · {data.data.period} · {data.data.hall.rows} ×{" "}
                {data.data.hall.columns} grid · capacity {data.data.hall.capacity}
              </p>
            </div>
            <Badge variant="secondary">
              {data.data.placed.length} placed · {data.data.unplaced.length} unplaced
            </Badge>
          </div>

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
                        <TableHead>Matric</TableHead>
                        <TableHead>Name</TableHead>
                        <TableHead>Course</TableHead>
                        <TableHead>Class</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.data.placed.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={5} className="text-center text-muted-foreground">
                            Nobody seated yet.
                          </TableCell>
                        </TableRow>
                      ) : (
                        data.data.placed
                          .sort((a, b) => (a.seat_number ?? 0) - (b.seat_number ?? 0))
                          .map((row) => (
                            <TableRow key={row.id}>
                              <TableCell className="font-medium">{row.seat_number}</TableCell>
                              <TableCell>{row.student?.matric_no}</TableCell>
                              <TableCell>
                                {row.student?.first_name} {row.student?.last_name}
                              </TableCell>
                              <TableCell>{row.course.code}</TableCell>
                              <TableCell>{row.class.name}</TableCell>
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
                        <TableHead>Matric</TableHead>
                        <TableHead>Name</TableHead>
                        <TableHead>Course</TableHead>
                        <TableHead>Class</TableHead>
                        {isAdmin && <TableHead className="w-[260px]">Manual seat</TableHead>}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.data.unplaced.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={isAdmin ? 5 : 4} className="text-center text-muted-foreground">
                            Everyone is seated.
                          </TableCell>
                        </TableRow>
                      ) : (
                        data.data.unplaced.map((row) => (
                          <TableRow key={row.id}>
                            <TableCell>{row.student?.matric_no}</TableCell>
                            <TableCell>
                              {row.student?.first_name} {row.student?.last_name}
                            </TableCell>
                            <TableCell>{row.course.code}</TableCell>
                            <TableCell>{row.class.name}</TableCell>
                            {isAdmin && (
                              <TableCell>
                                <div className="flex gap-2">
                                  <Input
                                    type="number"
                                    min={1}
                                    max={
                                      data.data?.hall.rows * data.data?.hall.columns
                                    }
                                    placeholder="Seat #"
                                    value={seatInputs[row.id] ?? ""}
                                    onChange={(e) =>
                                      setSeatInputs((s) => ({
                                        ...s,
                                        [row.id]: e.target.value,
                                      }))
                                    }
                                    className="w-24"
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
