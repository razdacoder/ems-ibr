import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  type Hall,
  useCreateHall,
  useDeleteHall,
  useHalls,
  useUpdateHall,
} from "@/api/halls";
import { Button } from "@/components/ui/button";
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
import { useConfirm } from "@/lib/confirm";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";

const schema = z.object({
  name: z.string().trim().min(1, "Name is required"),
  capacity: z.coerce.number().int().min(0),
  max_students: z.coerce.number().int().min(0),
  min_courses: z.coerce.number().int().min(0),
  rows: z.coerce.number().int().min(0),
  columns: z.coerce.number().int().min(0),
});

type Values = z.infer<typeof schema>;

export default function HallsListPage() {
  const { user } = useAuth();
  const isAdmin = !!user?.is_staff;

  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<Hall | null>(null);
  const [open, setOpen] = useState(false);

  const list = useHalls({ page, query: query || undefined });
  const remove = useDeleteHall();
  const confirm = useConfirm();

  const onDelete = async (h: Hall) => {
    const ok = await confirm({
      title: "Delete hall?",
      description: `Hall ${h.name} will be permanently removed.`,
      confirmLabel: "Delete",
      destructive: true,
    });
    if (!ok) return;
    try {
      await remove.mutateAsync(h.id);
      toast({ title: "Hall deleted" });
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
        title="Halls"
        description="Examination venues and their seating dimensions."
        toolbar={
          isAdmin && (
            <Button onClick={() => { setEditing(null); setOpen(true); }}>
              <Plus className="mr-2 h-4 w-4" /> New hall
            </Button>
          )
        }
        query={query}
        onQueryChange={(q) => { setQuery(q); setPage(1); }}
        searchPlaceholder="Search halls"
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
              <TableHead>Name</TableHead>
              <TableHead className="text-right">Capacity</TableHead>
              <TableHead className="text-right">Max students</TableHead>
              <TableHead className="text-right">Min courses</TableHead>
              <TableHead className="text-right">Rows × Cols</TableHead>
              {isAdmin && <TableHead className="w-[200px]">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.data?.results.map((h) => (
              <TableRow key={h.id}>
                <TableCell className="font-medium">{h.name}</TableCell>
                <TableCell className="text-right">{h.capacity}</TableCell>
                <TableCell className="text-right">{h.max_students}</TableCell>
                <TableCell className="text-right">{h.min_courses}</TableCell>
                <TableCell className="text-right">
                  {h.rows} × {h.columns}
                </TableCell>
                {isAdmin && (
                  <TableCell>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => { setEditing(h); setOpen(true); }}
                      >
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => onDelete(h)}
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
      <HallFormDialog open={open} onOpenChange={setOpen} initial={editing} />
    </>
  );
}

function HallFormDialog({
  open,
  onOpenChange,
  initial,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  initial: Hall | null;
}) {
  const isEdit = !!initial;
  const [topError, setTopError] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      capacity: 0,
      max_students: 0,
      min_courses: 0,
      rows: 0,
      columns: 0,
    },
  });
  const create = useCreateHall();
  const update = useUpdateHall(initial?.id ?? 0);

  useEffect(() => {
    if (!open) return;
    form.reset(
      initial ?? {
        name: "",
        capacity: 0,
        max_students: 0,
        min_courses: 0,
        rows: 0,
        columns: 0,
      },
    );
    setTopError(null);
  }, [open, initial, form]);

  const onSubmit = async (v: Values) => {
    setTopError(null);
    try {
      if (isEdit) {
        await update.mutateAsync(v);
        toast({ title: "Hall updated" });
      } else {
        await create.mutateAsync(v);
        toast({ title: "Hall created" });
      }
      onOpenChange(false);
    } catch (err) {
      const env = extractErrorEnvelope(err);
      setTopError(env.detail);
      if (env.errors) {
        for (const [k, msgs] of Object.entries(env.errors)) {
          if (
            ["name", "capacity", "max_students", "min_courses", "rows", "columns"].includes(k)
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
          <DialogTitle>{isEdit ? "Edit hall" : "New hall"}</DialogTitle>
          <DialogDescription>
            Hall capacity is the total seats available; rows × columns is the
            physical grid used for seat allocation.
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
                  <FormControl><Input {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="grid grid-cols-2 gap-3">
              {(
                [
                  ["capacity", "Capacity"],
                  ["max_students", "Max students"],
                  ["min_courses", "Min courses"],
                  ["rows", "Rows"],
                  ["columns", "Columns"],
                ] as const
              ).map(([name, label]) => (
                <FormField
                  key={name}
                  control={form.control}
                  name={name}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{label}</FormLabel>
                      <FormControl>
                        <Input type="number" min={0} {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              ))}
            </div>
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
