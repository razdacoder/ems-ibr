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
import { useConfirm } from "@/lib/confirm";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";
import { PaginationFooter } from "@/components/data-table/pagination";
import { PageHeader } from "@/components/layout/page-header";
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
  const confirm = useConfirm();

  const handleDelete = async (dept: Department) => {
    const ok = await confirm({
      title: "Delete department?",
      description: `"${dept.name}" will be permanently removed.`,
      confirmLabel: "Delete",
      destructive: true,
    });
    if (!ok) return;
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
    <div className="space-y-10">
      <PageHeader
        section="Catalog · Departments"
        title="Departments."
        description="Manage academic departments and their codes."
        actions={
          isAdmin && (
            <Button
              onClick={() => {
                setEditing(null);
                setDialogOpen(true);
              }}
              size="lg"
              className="h-10"
            >
              <Plus className="mr-1.5 h-4 w-4" strokeWidth={2.25} />
              New department
            </Button>
          )
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
          All departments
        </span>
        <div className="relative w-full sm:max-w-xs">
          <Search
            className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
            strokeWidth={2}
          />
          <Input
            placeholder="Search by name or code"
            className="h-9 pl-9 font-mono text-[12px]"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
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
                <TableHead className="w-[120px]">Code</TableHead>
                <TableHead>Department</TableHead>
                <TableHead className="w-[140px] text-right">Classes</TableHead>
                <TableHead className="w-[140px] text-right">Students</TableHead>
                {isAdmin && (
                  <TableHead className="w-[200px] text-right">Actions</TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.isLoading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <TableRow key={`s-${i}`}>
                    <TableCell colSpan={isAdmin ? 5 : 4}>
                      <Skeleton className="h-6 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              ) : list.data?.results.length ? (
                list.data.results.map((d) => (
                  <TableRow key={d.id}>
                    <TableCell>
                      <kbd className="rounded-[4px] border border-[color:var(--border)] bg-[color:var(--muted)] px-2 py-0.5 font-mono text-[11px] tracking-wide">
                        {d.slug}
                      </kbd>
                    </TableCell>
                    <TableCell className="font-serif text-[1.0625rem] tracking-[-0.005em]">
                      {d.name}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums">
                      {d.class_count.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums">
                      {d.student_count.toLocaleString()}
                    </TableCell>
                    {isAdmin && (
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
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
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={isAdmin ? 5 : 4}
                    className="py-12 text-center font-serif italic text-muted-foreground"
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
