import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  useEnableBulkUpload,
  useResetSystem,
  useSystemSettings,
  useUpdateSystemSettings,
} from "@/api/system";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { extractErrorEnvelope } from "@/lib/api";
import { toast } from "@/lib/use-toast";

const schema = z.object({
  session: z.string().trim().min(1, "Session is required"),
  semester: z.string().trim().min(1, "Semester is required"),
});

type Values = z.infer<typeof schema>;

export default function SettingsPage() {
  const settings = useSystemSettings();
  const update = useUpdateSystemSettings();
  const reset = useResetSystem();
  const enable = useEnableBulkUpload();

  const [topError, setTopError] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { session: "", semester: "" },
  });

  useEffect(() => {
    if (settings.data) {
      form.reset({
        session: settings.data.session,
        semester: settings.data.semester,
      });
    }
  }, [settings.data, form]);

  const onSubmit = async (v: Values) => {
    setTopError(null);
    try {
      await update.mutateAsync(v);
      toast({ title: "Settings updated" });
    } catch (err) {
      setTopError(extractErrorEnvelope(err).detail);
    }
  };

  const onReset = async () => {
    if (
      !confirm(
        "Reset the system? Every department, class, course, hall, student, timetable and seat allocation will be deleted.",
      )
    )
      return;
    try {
      await reset.mutateAsync();
      toast({ title: "System reset complete" });
    } catch (err) {
      toast({
        title: "Reset failed",
        description: extractErrorEnvelope(err).detail,
        variant: "destructive",
      });
    }
  };

  const onEnableBulk = async () => {
    try {
      await enable.mutateAsync();
      toast({ title: "Bulk upload enabled" });
    } catch (err) {
      toast({
        title: "Could not enable",
        description: extractErrorEnvelope(err).detail,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">System settings</h1>
        <p className="text-sm text-muted-foreground">
          Configure the active session and semester, and manage destructive admin
          actions.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Session and semester</CardTitle>
          <CardDescription>
            These labels appear on every export and report.
          </CardDescription>
        </CardHeader>
        {settings.isLoading ? (
          <CardContent>
            <Skeleton className="h-32 w-full" />
          </CardContent>
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)}>
              <CardContent className="space-y-4">
                {topError && (
                  <Alert variant="destructive">
                    <AlertDescription>{topError}</AlertDescription>
                  </Alert>
                )}
                <FormField
                  control={form.control}
                  name="session"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Academic session</FormLabel>
                      <FormControl>
                        <Input placeholder="2024/2025" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="semester"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Semester</FormLabel>
                      <FormControl>
                        <Input placeholder="1st Semester" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </CardContent>
              <CardFooter className="justify-end">
                <Button type="submit" disabled={form.formState.isSubmitting}>
                  {form.formState.isSubmitting ? "Saving…" : "Save changes"}
                </Button>
              </CardFooter>
            </form>
          </Form>
        )}
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Upload lock</CardTitle>
          <CardDescription>
            Once a timetable is generated, file uploads are locked. Re-enable to
            modify departments, classes, courses, or students.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {settings.data?.has_timetable ? (
            <Alert>
              <AlertTitle>Uploads currently locked</AlertTitle>
              <AlertDescription>
                A timetable already exists. Click below if you need to allow
                further uploads.
              </AlertDescription>
            </Alert>
          ) : (
            <p className="text-sm text-muted-foreground">
              Uploads are open. Generating a timetable will lock them
              automatically.
            </p>
          )}
        </CardContent>
        <CardFooter className="justify-end">
          <Button
            variant="outline"
            onClick={onEnableBulk}
            disabled={enable.isPending || !settings.data?.has_timetable}
          >
            Re-enable uploads
          </Button>
        </CardFooter>
      </Card>

      <Card className="border-destructive/40">
        <CardHeader>
          <CardTitle className="text-destructive">Reset the system</CardTitle>
          <CardDescription>
            Wipe all departments, classes, courses, halls, students, timetables
            and seat allocations. This cannot be undone.
          </CardDescription>
        </CardHeader>
        <CardFooter className="justify-end">
          <Button
            variant="destructive"
            onClick={onReset}
            disabled={reset.isPending}
          >
            {reset.isPending ? "Resetting…" : "Reset everything"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
