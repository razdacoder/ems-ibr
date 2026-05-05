import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  useAddCourseToClass,
  useClass,
  useRemoveCourseFromClass,
} from "@/api/classes";
import {
  useUploadClassCourses,
  useUploadClassStudents,
} from "@/api/uploads";
import { useSystemSettings } from "@/api/system";
import { FileUploadCard } from "@/components/file-upload-card";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/lib/auth";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";

export default function ClassDetailPage() {
  const { id } = useParams<{ id: string }>();
  const numericId = id ? Number(id) : undefined;
  const cls = useClass(numericId);
  const remove = useRemoveCourseFromClass(numericId ?? 0);
  const { user } = useAuth();
  const isAdmin = !!user?.is_staff;
  const [open, setOpen] = useState(false);

  const onRemove = async (courseId: number, code: string) => {
    if (!confirm(`Remove ${code} from this class?`)) return;
    try {
      await remove.mutateAsync(courseId);
      toast({ title: "Course removed" });
    } catch (err) {
      toast({
        title: "Remove failed",
        description: extractErrorEnvelope(err).detail,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-10">
      <Link
        to="/classes"
        className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-3" strokeWidth={2.25} />
        Back to classes
      </Link>

      {cls.isLoading ? (
        <Skeleton className="h-32" />
      ) : cls.data ? (
        <>
          <header className="flex flex-col gap-6 border-b border-[color:var(--border)] pb-8 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                § Catalog · Class
              </p>
              <h1 className="mt-3 font-serif text-[2.5rem] leading-[1.05] tracking-[-0.015em] sm:text-[3rem]">
                {cls.data.name}.
              </h1>
              <p className="mt-2 text-[14.5px] text-muted-foreground">
                {cls.data.department.name}
                <span className="ml-2 font-mono text-[11px] uppercase tracking-[0.12em]">
                  {cls.data.department.slug}
                </span>
              </p>
            </div>
            <div className="rounded-[10px] border border-[color:var(--border)] bg-card px-5 py-4 text-right">
              <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                Students enrolled
              </p>
              <p className="mt-1 font-serif text-[2rem] tabular-nums">
                {cls.data.student_count}
              </p>
            </div>
          </header>

          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <div>
                <CardTitle className="text-base">Courses</CardTitle>
                <CardDescription>
                  Courses currently linked to this class.
                </CardDescription>
              </div>
              {isAdmin && numericId !== undefined && (
                <Button onClick={() => setOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" /> Add course
                </Button>
              )}
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[140px]">Code</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead className="w-[120px]">Type</TableHead>
                    {isAdmin && (
                      <TableHead className="w-[80px] text-right" />
                    )}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {cls.data.courses.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={isAdmin ? 4 : 3}
                        className="py-12 text-center font-serif italic text-muted-foreground"
                      >
                        No courses assigned yet.
                      </TableCell>
                    </TableRow>
                  ) : (
                    cls.data.courses.map((c) => (
                      <TableRow key={c.id}>
                        <TableCell>
                          <span className="font-mono text-[12px] tracking-wide">
                            {c.code}
                          </span>
                        </TableCell>
                        <TableCell className="font-serif text-[1rem] tracking-[-0.005em]">
                          {c.name}
                        </TableCell>
                        <TableCell>
                          <span
                            className="rounded-full px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em]"
                            style={
                              c.exam_type === "CBE"
                                ? {
                                    backgroundColor: "var(--accent-blue)",
                                    color: "var(--accent-blue-fg)",
                                  }
                                : {
                                    backgroundColor: "var(--accent-yellow)",
                                    color: "var(--accent-yellow-fg)",
                                  }
                            }
                          >
                            {c.exam_type}
                          </span>
                        </TableCell>
                        {isAdmin && (
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => onRemove(c.id, c.code)}
                              disabled={remove.isPending}
                              title={`Remove ${c.code}`}
                            >
                              <Trash2 className="h-4 w-4" strokeWidth={2} />
                            </Button>
                          </TableCell>
                        )}
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {numericId !== undefined && isAdmin && (
            <ClassUploadGrid classId={numericId} />
          )}

          {numericId !== undefined && (
            <AddCourseDialog
              open={open}
              onOpenChange={setOpen}
              classId={numericId}
            />
          )}
        </>
      ) : null}
    </div>
  );
}

function ClassUploadGrid({ classId }: { classId: number }) {
  const settings = useSystemSettings();
  const locked = !!settings.data?.has_timetable;
  const courseUpload = useUploadClassCourses(classId);
  const studentUpload = useUploadClassStudents(classId);
  const [coursesResult, setCoursesResult] =
    useState<{ created: number; updated: number } | null>(null);
  const [studentsResult, setStudentsResult] =
    useState<{ created: number; updated: number } | null>(null);

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <FileUploadCard
        title="Upload class courses"
        description="CSV with a single COURSE CODE column. Courses must already exist in the catalog."
        disabled={locked}
        isPending={courseUpload.isPending}
        result={coursesResult}
        error={courseUpload.error}
        onUpload={async (file) => {
          const r = await courseUpload.mutateAsync(file);
          setCoursesResult(r);
          toast({
            title: "Courses linked",
            description: `Added ${r.created}, already-linked ${r.updated}`,
          });
        }}
      />
      <FileUploadCard
        title="Upload class students"
        description="CSV columns: MATRIC NUMBER, FIRSTNAME, LASTNAME, EMAIL, PHONE NUMBER"
        disabled={locked}
        isPending={studentUpload.isPending}
        result={studentsResult}
        error={studentUpload.error}
        onUpload={async (file) => {
          const r = await studentUpload.mutateAsync(file);
          setStudentsResult(r);
          toast({
            title: "Students uploaded",
            description: `Created ${r.created}, updated ${r.updated}`,
          });
        }}
      />
    </div>
  );
}

const schema = z.object({
  name: z.string().trim().min(1, "Title is required"),
  code: z.string().trim().min(1, "Code is required"),
  exam_type: z.enum(["PBE", "CBE"]),
});
type Values = z.infer<typeof schema>;

function AddCourseDialog({
  open,
  onOpenChange,
  classId,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  classId: number;
}) {
  const [topError, setTopError] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", code: "", exam_type: "PBE" },
  });
  const add = useAddCourseToClass(classId);

  const onSubmit = async (v: Values) => {
    setTopError(null);
    try {
      await add.mutateAsync({
        name: v.name.trim(),
        code: v.code.trim().toUpperCase(),
        exam_type: v.exam_type,
      });
      toast({ title: "Course added" });
      onOpenChange(false);
      form.reset();
    } catch (err) {
      const env = extractErrorEnvelope(err);
      setTopError(env.detail);
      if (env.errors) {
        for (const [k, msgs] of Object.entries(env.errors)) {
          if (k === "name" || k === "code") {
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
          <DialogTitle>Add course to class</DialogTitle>
          <DialogDescription>
            If a course with this code already exists, it will be linked here.
            Otherwise a new course is created.
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
              name="code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Code</FormLabel>
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
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Title</FormLabel>
                  <FormControl><Input {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="exam_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Exam type</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="PBE">PBE</SelectItem>
                      <SelectItem value="CBE">CBE</SelectItem>
                    </SelectContent>
                  </Select>
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
                {form.formState.isSubmitting ? "Adding…" : "Add"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
