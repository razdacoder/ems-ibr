import { useSchool } from "@/api/platform";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { extractErrorEnvelope } from "@/lib/api";
import { SchoolForm } from "./school-form";

export default function ConsoleEditSchoolPage({ id }: { id: number }) {
  const school = useSchool(id);

  if (school.isLoading) {
    return (
      <div className="space-y-8">
        <Skeleton className="h-12 w-2/3" />
        <Skeleton className="h-96" />
      </div>
    );
  }
  if (school.error || !school.data) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{extractErrorEnvelope(school.error).detail}</AlertDescription>
      </Alert>
    );
  }
  return <SchoolForm school={school.data} />;
}
