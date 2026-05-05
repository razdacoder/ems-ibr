import { useState } from "react";
import { Plus, Search } from "lucide-react";
import {
  type Department,
  useDeleteDepartment,
  useDepartments,
} from "@/api/departments";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
import { useAuth } from "@/lib/auth";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";
import { PaginationFooter } from "@/components/data-table/pagination";
import { DepartmentFormDialog } from "./department-form-dialog";

export default function DepartmentsListPage() {
  const { user } = useAuth();
  const isAdmin = !!user?.is_staff;

  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Department | null>(null);

  const list = useDepartments({ page, query: query || undefined });
  const remove = useDeleteDepartment();

  const handleDelete = async (dept: Department) => {
    if (!confirm(`Delete department "${dept.name}"?`)) return;
    try {
      await remove.mutateAsync(dept.slug);
      toast({ title: "Department deleted" });
    } catch (err) {
      const envelope = extractErrorEnvelope(err);
      toast({
        title: "Delete failed",
        description: envelope.detail,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-semibold">Departments</h1>
          <p className="text-sm text-muted-foreground">
            Manage academic departments and their codes.
          </p>
        </div>
        {isAdmin && (
          <Button
            onClick={() => {
              setEditing(null);
              setDialogOpen(true);
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            New department
          </Button>
        )}
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base">All departments</CardTitle>
          <div className="relative w-full max-w-xs">
            <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by name or code"
              className="pl-8"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
            />
          </div>
        </CardHeader>
        <CardContent>
          {list.error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>
                {extractErrorEnvelope(list.error).detail}
              </AlertDescription>
            </Alert>
          )}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead className="text-right">Classes</TableHead>
                <TableHead className="text-right">Students</TableHead>
                {isAdmin && <TableHead className="w-[200px]">Actions</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.isLoading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <TableRow key={`s-${i}`}>
                      <TableCell colSpan={isAdmin ? 5 : 4}>
                        <Skeleton className="h-6 w-full" />
                      </TableCell>
                    </TableRow>
                  ))
                : list.data?.results.length
                  ? list.data.results.map((d) => (
                      <TableRow key={d.id}>
                        <TableCell className="font-medium">{d.slug}</TableCell>
                        <TableCell>{d.name}</TableCell>
                        <TableCell className="text-right">
                          {d.class_count}
                        </TableCell>
                        <TableCell className="text-right">
                          {d.student_count}
                        </TableCell>
                        {isAdmin && (
                          <TableCell>
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setEditing(d);
                                  setDialogOpen(true);
                                }}
                              >
                                Edit
                              </Button>
                              <Button
                                size="sm"
                                variant="destructive"
                                onClick={() => handleDelete(d)}
                                disabled={remove.isPending}
                              >
                                Delete
                              </Button>
                            </div>
                          </TableCell>
                        )}
                      </TableRow>
                    ))
                  : (
                      <TableRow>
                        <TableCell
                          colSpan={isAdmin ? 5 : 4}
                          className="text-center text-muted-foreground"
                        >
                          No departments found.
                        </TableCell>
                      </TableRow>
                    )}
            </TableBody>
          </Table>
          {list.data && (
            <PaginationFooter
              page={page}
              pageSize={15}
              total={list.data.count}
              onPageChange={setPage}
            />
          )}
        </CardContent>
      </Card>

      <DepartmentFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        initial={editing}
      />
    </div>
  );
}
