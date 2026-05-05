import { useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  type UserRow,
  useChangeUserPassword,
  useCreateUser,
  useDeleteUser,
  useUpdateUser,
  useUsers,
} from "@/api/users";
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
import { Badge } from "@/components/ui/badge";
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

export default function UsersListPage() {
  const { user: me } = useAuth();
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<UserRow | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [pwUser, setPwUser] = useState<UserRow | null>(null);
  const [pwOpen, setPwOpen] = useState(false);

  const list = useUsers({ page, query: query || undefined });
  const remove = useDeleteUser();

  const onDelete = async (u: UserRow) => {
    if (!confirm(`Delete user ${u.email}?`)) return;
    try {
      await remove.mutateAsync(u.id);
      toast({ title: "User deleted" });
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
        title="Users"
        description="Application users — admins and department staff."
        toolbar={
          <Button onClick={() => { setEditing(null); setEditOpen(true); }}>
            <Plus className="mr-2 h-4 w-4" /> New user
          </Button>
        }
        query={query}
        onQueryChange={(q) => { setQuery(q); setPage(1); }}
        searchPlaceholder="Search by name or email"
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
              <TableHead>Email</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Department</TableHead>
              <TableHead>Role</TableHead>
              <TableHead className="w-[280px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.data?.results.map((u) => (
              <TableRow key={u.id}>
                <TableCell className="font-medium">{u.email}</TableCell>
                <TableCell>{u.full_name}</TableCell>
                <TableCell>{u.department?.slug ?? "—"}</TableCell>
                <TableCell>
                  <Badge variant={u.is_staff ? "default" : "secondary"}>
                    {u.is_staff ? "Admin" : "Staff"}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => { setEditing(u); setEditOpen(true); }}
                    >
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => { setPwUser(u); setPwOpen(true); }}
                    >
                      Password
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => onDelete(u)}
                      disabled={remove.isPending || u.id === me?.id}
                    >
                      Delete
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ListShell>
      <UserFormDialog open={editOpen} onOpenChange={setEditOpen} initial={editing} />
      <ChangePasswordDialog open={pwOpen} onOpenChange={setPwOpen} user={pwUser} />
    </>
  );
}

const userSchema = z.object({
  email: z.string().email("Valid email required"),
  first_name: z.string().trim().min(1),
  last_name: z.string().trim().min(1),
  is_staff: z.boolean(),
  department_id: z.coerce.number().int().nullable(),
  password: z.string().min(8, "At least 8 characters").or(z.literal("")),
});

type UserValues = z.infer<typeof userSchema>;

function UserFormDialog({
  open,
  onOpenChange,
  initial,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  initial: UserRow | null;
}) {
  const isEdit = !!initial;
  const [topError, setTopError] = useState<string | null>(null);
  const form = useForm<UserValues>({
    resolver: zodResolver(userSchema),
    defaultValues: {
      email: "",
      first_name: "",
      last_name: "",
      is_staff: false,
      department_id: null,
      password: "",
    },
  });
  const create = useCreateUser();
  const update = useUpdateUser(initial?.id ?? 0);
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
            email: initial.email,
            first_name: initial.first_name,
            last_name: initial.last_name,
            is_staff: initial.is_staff,
            department_id: initial.department?.id ?? null,
            password: "",
          }
        : {
            email: "",
            first_name: "",
            last_name: "",
            is_staff: false,
            department_id: null,
            password: "",
          },
    );
    setTopError(null);
  }, [open, initial, form]);

  const onSubmit = async (v: UserValues) => {
    setTopError(null);
    const payload: Record<string, unknown> = {
      email: v.email.trim(),
      first_name: v.first_name.trim(),
      last_name: v.last_name.trim(),
      is_staff: v.is_staff,
      department_id: v.is_staff ? null : v.department_id,
    };
    if (v.password) payload.password = v.password;
    try {
      if (isEdit) {
        await update.mutateAsync(payload);
        toast({ title: "User updated" });
      } else {
        if (!v.password) {
          form.setError("password", { message: "Password is required" });
          return;
        }
        await create.mutateAsync(payload as never);
        toast({ title: "User created" });
      }
      onOpenChange(false);
    } catch (err) {
      const env = extractErrorEnvelope(err);
      setTopError(env.detail);
      if (env.errors) {
        for (const [k, msgs] of Object.entries(env.errors)) {
          if (
            ["email", "first_name", "last_name", "password", "department_id", "is_staff"].includes(k)
          ) {
            form.setError(k as keyof UserValues, { message: msgs.join(", ") });
          }
        }
      }
    }
  };

  const isStaff = form.watch("is_staff");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit user" : "New user"}</DialogTitle>
          <DialogDescription>
            Admin users can manage every department; non-admin users are scoped
            to one department.
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
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl><Input type="email" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
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
              name="is_staff"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Role</FormLabel>
                  <Select
                    value={field.value ? "admin" : "staff"}
                    onValueChange={(v) => field.onChange(v === "admin")}
                  >
                    <FormControl>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="staff">Staff (department-scoped)</SelectItem>
                      <SelectItem value="admin">Admin (full access)</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            {!isStaff && (
              <FormField
                control={form.control}
                name="department_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Department</FormLabel>
                    <Select
                      value={field.value ? String(field.value) : ""}
                      onValueChange={(v) =>
                        field.onChange(v === "" ? null : Number(v))
                      }
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Pick a department" />
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
            )}
            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    {isEdit ? "Password (leave blank to keep current)" : "Password"}
                  </FormLabel>
                  <FormControl><Input type="password" {...field} /></FormControl>
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

const pwSchema = z
  .object({
    password: z.string().min(8, "At least 8 characters"),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, {
    message: "Passwords do not match",
    path: ["confirm"],
  });

type PwValues = z.infer<typeof pwSchema>;

function ChangePasswordDialog({
  open,
  onOpenChange,
  user,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  user: UserRow | null;
}) {
  const [topError, setTopError] = useState<string | null>(null);
  const form = useForm<PwValues>({
    resolver: zodResolver(pwSchema),
    defaultValues: { password: "", confirm: "" },
  });
  const change = useChangeUserPassword(user?.id ?? 0);

  useEffect(() => {
    if (open) {
      form.reset({ password: "", confirm: "" });
      setTopError(null);
    }
  }, [open, form]);

  const onSubmit = async (v: PwValues) => {
    setTopError(null);
    try {
      await change.mutateAsync(v.password);
      toast({ title: "Password changed" });
      onOpenChange(false);
    } catch (err) {
      setTopError(extractErrorEnvelope(err).detail);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change password</DialogTitle>
          <DialogDescription>
            Set a new password for {user?.email}. Their existing API token will be
            invalidated.
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
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>New password</FormLabel>
                  <FormControl><Input type="password" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="confirm"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Confirm</FormLabel>
                  <FormControl><Input type="password" {...field} /></FormControl>
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
                {form.formState.isSubmitting ? "Saving…" : "Change password"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
