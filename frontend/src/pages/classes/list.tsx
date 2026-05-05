import { useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  type Class,
  useClasses,
  useCreateClass,
  useDeleteClass,
  useUpdateClass,
} from "@/api/classes";
import { useDepartments } from "@/api/departments";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { ListShell } from "@/components/data-table/list-shell";
import { PaginationFooter } from "@/components/data-table/pagination";
import { useAuth } from "@/lib/auth";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";
import { Link } from "react-router-dom";

export default function ClassesListPage() {
  const { user } = useAuth();
  const isAdmin = !!user?.is_staff;
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [department, setDepartment] = useState<string>("__all__");
  const [editing, setEditing] = useState<Class | null>(null);
  const [open, setOpen] = useState(false);

  const list = useClasses({
    page,
    query: query || undefined,
    department: department === "__all__" ? undefined : department,
  });
  const remove = useDeleteClass();
  const departments = useDepartments({ page: 1 });

  const onDelete = async (c: Class) => {
    if (!confirm(`Delete class "${c.name}"?`)) return;
    try {
      await remove.mutateAsync(c.id);
      toast({ title: "Class deleted" });
    } catch (err) {
      toast({
        title: "Delete failed",
        description: extractErrorEnvelope(err).detail,
        variant: "destructive",
      });
    }
  };

  return (
    <>
      <ListShell
        title="Classes"
        description="Class cohorts grouped under each department."
        toolbar={
          isAdmin && (
            <Button onClick={() => { setEditing(null); setOpen(true); }}>
              <Plus className="mr-2 h-4 w-4" /> New class
            </Button>
          )
        }
        query={query}
        onQueryChange={(q) => { setQuery(q); setPage(1); }}
        searchPlaceholder="Search by class name"
        filters={
          <Select
            value={department}
            onValueChange={(v) => { setDepartment(v); setPage(1); }}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All departments" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All departments</SelectItem>
              {departments.data?.results.map((d) => (
                <SelectItem key={d.id} value={d.slug}>
                  {d.slug}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
        isLoading={list.isLoading}
        error={list.error}
        isEmpty={!list.data?.results.length}
        pagination={
          list.data && (
            <PaginationFooter
              page={page}
              pageSize={15}
              total={list.data.count}
              onPageChange={setPage}
            />
          )
        }
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Class</TableHead>
              <TableHead>Department</TableHead>
              <TableHead className="text-right">Students</TableHead>
              <TableHead>Courses</TableHead>
              {isAdmin && <TableHead className="w-[260px]">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.data?.results.map((c) => (
              <TableRow key={c.id}>
                <TableCell className="font-medium">{c.name}</TableCell>
                <TableCell>{c.department.slug}</TableCell>
                <TableCell className="text-right">{c.student_count}</TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {c.courses.slice(0, 5).map((co) => (
                      <Badge key={co.id} variant="secondary">{co.code}</Badge>
                    ))}
                    {c.courses.length > 5 && (
                      <Badge variant="outline">+{c.courses.length - 5}</Badge>
                    )}
                  </div>
                </TableCell>
                {isAdmin && (
                  <TableCell>
                    <div className="flex gap-2">
                      <Button asChild size="sm" variant="outline">
                        <Link to={`/classes/${c.id}`}>Manage</Link>
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => { setEditing(c); setOpen(true); }}
                      >
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => onDelete(c)}
                        disabled={remove.isPending}
                      >
                        Delete
                      </Button>
                    </div>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ListShell>
      <ClassFormDialog open={open} onOpenChange={setOpen} initial={editing} />
    </>
  );
}

const schema = z.object({
  name: z.string().trim().min(1, "Class name is required"),
  size: z.coerce.number().int().min(0),
  department_id: z.coerce.number().int().min(1, "Pick a department"),
});

type Values = z.infer<typeof schema>;

function ClassFormDialog({
  open,
  onOpenChange,
  initial,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  initial: Class | null;
}) {
  const isEdit = !!initial;
  const [topError, setTopError] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", size: 0, department_id: 0 },
  });
  const create = useCreateClass();
  const update = useUpdateClass(initial?.id ?? 0);
  const departments = useDepartments({ page: 1 });

  const departmentOptions = useMemo(
    () => departments.data?.results ?? [],
    [departments.data],
  );

  useEffect(() => {
    if (!open) return;
    form.reset(
      initial
        ? {
            name: initial.name ?? "",
            size: initial.size,
            department_id: initial.department.id,
          }
        : { name: "", size: 0, department_id: 0 },
    );
    setTopError(null);
  }, [open, initial, form]);

  const onSubmit = async (v: Values) => {
    setTopError(null);
    try {
      if (isEdit) {
        await update.mutateAsync({ name: v.name, size: v.size });
        toast({ title: "Class updated" });
      } else {
        await create.mutateAsync(v);
        toast({ title: "Class created" });
      }
      onOpenChange(false);
    } catch (err) {
      const env = extractErrorEnvelope(err);
      setTopError(env.detail);
      if (env.errors) {
        for (const [k, msgs] of Object.entries(env.errors)) {
          if (k === "name" || k === "size" || k === "department_id") {
            form.setError(k, { message: msgs.join(", ") });
          }
        }
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit class" : "New class"}</DialogTitle>
          <DialogDescription>
            Class size is auto-recalculated from enrolled students.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-3">
            {topError && (
              <Alert variant="destructive">
                <AlertDescription>{topError}</AlertDescription>
              </Alert>
            )}
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input placeholder="100 Level" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="department_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Department</FormLabel>
                  <Select
                    value={field.value ? String(field.value) : ""}
                    onValueChange={(v) => field.onChange(Number(v))}
                    disabled={isEdit}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a department" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {departmentOptions.map((d) => (
                        <SelectItem key={d.id} value={String(d.id)}>
                          {d.slug} — {d.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="size"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Size</FormLabel>
                  <FormControl>
                    <Input type="number" min={0} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting
                  ? "Saving…"
                  : isEdit
                    ? "Save changes"
                    : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
