import { useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  type Student,
  useCreateStudent,
  useDeleteStudent,
  useStudents,
  useUpdateStudent,
} from "@/api/students";
import { useClasses } from "@/api/classes";
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
import { ListShell } from "@/components/data-table/list-shell";
import { PaginationFooter } from "@/components/data-table/pagination";
import { useAuth } from "@/lib/auth";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";

export default function StudentsListPage() {
  const { user } = useAuth();
  const isAdmin = !!user?.is_staff;
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [department, setDepartment] = useState<string>("__all__");
  const [classFilter, setClassFilter] = useState<string>("__all__");
  const [editing, setEditing] = useState<Student | null>(null);
  const [open, setOpen] = useState(false);

  const list = useStudents({
    page,
    query: query || undefined,
    department: department === "__all__" ? undefined : department,
    class: classFilter === "__all__" ? undefined : Number(classFilter),
  });
  const remove = useDeleteStudent();
  const departments = useDepartments({ page: 1 });
  const classes = useClasses({ page: 1 });

  const onDelete = async (s: Student) => {
    if (!confirm(`Delete ${s.matric_no}?`)) return;
    try {
      await remove.mutateAsync(s.id);
      toast({ title: "Student deleted" });
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
        title="Students"
        description="Enrolled students grouped by department and class."
        toolbar={
          isAdmin && (
            <Button onClick={() => { setEditing(null); setOpen(true); }}>
              <Plus className="mr-2 h-4 w-4" /> New student
            </Button>
          )
        }
        query={query}
        onQueryChange={(q) => { setQuery(q); setPage(1); }}
        searchPlaceholder="Search by name or matric"
        filters={
          <>
            <Select
              value={department}
              onValueChange={(v) => { setDepartment(v); setPage(1); }}
            >
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Department" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All depts</SelectItem>
                {departments.data?.results.map((d) => (
                  <SelectItem key={d.id} value={d.slug}>
                    {d.slug}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={classFilter}
              onValueChange={(v) => { setClassFilter(v); setPage(1); }}
            >
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Class" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All classes</SelectItem>
                {classes.data?.results.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>
                    {c.department.slug} {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </>
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
              <TableHead>Matric</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Class</TableHead>
              {isAdmin && <TableHead className="w-[200px]">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.data?.results.map((s) => (
              <TableRow key={s.id}>
                <TableCell className="font-medium">{s.matric_no}</TableCell>
                <TableCell>
                  {s.first_name} {s.last_name}
                </TableCell>
                <TableCell className="text-muted-foreground">{s.email}</TableCell>
                <TableCell>
                  {s.department?.slug} {s.level?.name}
                </TableCell>
                {isAdmin && (
                  <TableCell>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => { setEditing(s); setOpen(true); }}
                      >
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => onDelete(s)}
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
      <StudentFormDialog
        open={open}
        onOpenChange={setOpen}
        initial={editing}
      />
    </>
  );
}

const schema = z.object({
  first_name: z.string().trim().min(1, "Required"),
  last_name: z.string().trim().min(1, "Required"),
  matric_no: z.string().trim().min(1, "Required"),
  email: z.string().trim().email("Valid email required").or(z.literal("")),
  phone: z.string().trim().max(15).or(z.literal("")),
  class_id: z.coerce.number().int().min(1, "Pick a class"),
});

type Values = z.infer<typeof schema>;

function StudentFormDialog({
  open,
  onOpenChange,
  initial,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  initial: Student | null;
}) {
  const isEdit = !!initial;
  const [topError, setTopError] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      first_name: "",
      last_name: "",
      matric_no: "",
      email: "",
      phone: "",
      class_id: 0,
    },
  });
  const create = useCreateStudent();
  const update = useUpdateStudent(initial?.id ?? 0);
  const classes = useClasses({ page: 1 });
  const classOptions = useMemo(() => classes.data?.results ?? [], [classes.data]);

  useEffect(() => {
    if (!open) return;
    form.reset(
      initial
        ? {
            first_name: initial.first_name,
            last_name: initial.last_name,
            matric_no: initial.matric_no,
            email: initial.email,
            phone: initial.phone,
            class_id: initial.level?.id ?? 0,
          }
        : {
            first_name: "",
            last_name: "",
            matric_no: "",
            email: "",
            phone: "",
            class_id: 0,
          },
    );
    setTopError(null);
  }, [open, initial, form]);

  const onSubmit = async (v: Values) => {
    setTopError(null);
    const payload = {
      first_name: v.first_name.trim(),
      last_name: v.last_name.trim(),
      matric_no: v.matric_no.trim().toUpperCase(),
      email: v.email,
      phone: v.phone,
      class_id: v.class_id,
    };
    try {
      if (isEdit) {
        const { class_id: _ignored, ...rest } = payload;
        await update.mutateAsync(rest);
        toast({ title: "Student updated" });
      } else {
        await create.mutateAsync(payload);
        toast({ title: "Student created" });
      }
      onOpenChange(false);
    } catch (err) {
      const env = extractErrorEnvelope(err);
      setTopError(env.detail);
      if (env.errors) {
        for (const [k, msgs] of Object.entries(env.errors)) {
          if (
            ["first_name", "last_name", "matric_no", "email", "phone", "class_id"].includes(k)
          ) {
            form.setError(k as keyof Values, { message: msgs.join(", ") });
          }
        }
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Edit student" : "New student"}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Update the student's profile fields."
              : "Add a new student to a class. Department is inferred from the class."}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-3">
            {topError && (
              <Alert variant="destructive">
                <AlertDescription>{topError}</AlertDescription>
              </Alert>
            )}
            <div className="grid grid-cols-2 gap-3">
              <FormField
                control={form.control}
                name="first_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>First name</FormLabel>
                    <FormControl><Input {...field} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="last_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Last name</FormLabel>
                    <FormControl><Input {...field} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <FormField
              control={form.control}
              name="matric_no"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Matric number</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      onChange={(e) =>
                        field.onChange(e.target.value.toUpperCase())
                      }
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="grid grid-cols-2 gap-3">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input type="email" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="phone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Phone</FormLabel>
                    <FormControl><Input {...field} /></FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            {!isEdit && (
              <FormField
                control={form.control}
                name="class_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Class</FormLabel>
                    <Select
                      value={field.value ? String(field.value) : ""}
                      onValueChange={(v) => field.onChange(Number(v))}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Pick a class" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {classOptions.map((c) => (
                          <SelectItem key={c.id} value={String(c.id)}>
                            {c.department.slug} {c.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
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
