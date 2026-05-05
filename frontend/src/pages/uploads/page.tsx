import { useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FileUploadCard } from "@/components/file-upload-card";
import {
  useUploadCourses,
  useUploadDepartments,
  useUploadHalls,
} from "@/api/uploads";
import {
  useEnableBulkUpload,
  useSystemSettings,
} from "@/api/system";
import { toast } from "@/lib/use-toast";
import { extractErrorEnvelope } from "@/lib/api";

export default function UploadsPage() {
  const settings = useSystemSettings();
  const enable = useEnableBulkUpload();
  const locked = !!settings.data?.has_timetable;

  const departments = useUploadDepartments();
  const halls = useUploadHalls();
  const courses = useUploadCourses();

  const [departmentsResult, setDepartmentsResult] =
    useState<{ created: number; updated: number } | null>(null);
  const [hallsResult, setHallsResult] =
    useState<{ created: number; updated: number } | null>(null);
  const [coursesResult, setCoursesResult] =
    useState<{ created: number; updated: number } | null>(null);

  const onEnable = async () => {
    try {
      await enable.mutateAsync();
      toast({ title: "Uploads re-enabled" });
    } catch (err) {
      toast({
        title: "Could not unlock",
        description: extractErrorEnvelope(err).detail,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Bulk uploads</h1>
        <p className="text-sm text-muted-foreground">
          Import departments, halls, and the institutional course catalog from
          CSV files. Class- and student-level uploads happen on the class detail
          page.
        </p>
      </div>

      {locked && (
        <Alert>
          <AlertTitle>Uploads are locked</AlertTitle>
          <AlertDescription className="flex items-center justify-between gap-3">
            <span>
              A timetable already exists. Re-enable uploads to ingest new data.
            </span>
            <Button
              size="sm"
              variant="outline"
              onClick={onEnable}
              disabled={enable.isPending}
            >
              Re-enable
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <FileUploadCard
          title="Departments"
          description="CSV columns: Name, Code"
          disabled={locked}
          isPending={departments.isPending}
          result={departmentsResult}
          error={departments.error}
          onUpload={async (file) => {
            const r = await departments.mutateAsync(file);
            setDepartmentsResult(r);
            toast({
              title: "Departments uploaded",
              description: `Created ${r.created}, updated ${r.updated}`,
            });
          }}
        />
        <FileUploadCard
          title="Halls"
          description="CSV columns: EXAM VENUE, CAPACITY, MAX STUDENTS, MIN COURSES, ROWS, COLS"
          disabled={locked}
          isPending={halls.isPending}
          result={hallsResult}
          error={halls.error}
          onUpload={async (file) => {
            const r = await halls.mutateAsync(file);
            setHallsResult(r);
            toast({
              title: "Halls uploaded",
              description: `Created ${r.created}, updated ${r.updated}`,
            });
          }}
        />
        <FileUploadCard
          title="Courses"
          description="CSV columns: COURSE CODE, COURSE TITLE, EXAM TYPE (PBE/CBE)"
          disabled={locked}
          isPending={courses.isPending}
          result={coursesResult}
          error={courses.error}
          onUpload={async (file) => {
            const r = await courses.mutateAsync(file);
            setCoursesResult(r);
            toast({
              title: "Courses uploaded",
              description: `Created ${r.created}, updated ${r.updated}`,
            });
          }}
        />
      </div>
    </div>
  );
}
