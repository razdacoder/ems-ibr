import { useSchoolPlan } from "@/api/school";
import { cn } from "@/lib/utils";

const NOUNS = {
  students: ["student", "students", "max_students"],
  staff_users: ["staff account", "staff accounts", "max_staff_users"],
} as const;

/**
 * "1,240 of 2,000 students used", when the school's plan caps them. Shown in
 * the destructive colour once the cap is reached. Nothing for unlimited.
 */
export function PlanUsage({ kind, className }: { kind: keyof typeof NOUNS; className?: string }) {
  const plan = useSchoolPlan();
  if (!plan.data) return null;
  const [one, many, limitKey] = NOUNS[kind];
  const cap = plan.data.limits[limitKey];
  if (cap === null) return null;
  const used = plan.data.usage[kind];
  const full = used >= cap;
  return (
    <span
      className={cn(
        "font-mono text-[11px] tabular-nums",
        full ? "text-destructive" : "text-muted-foreground",
        className,
      )}
      title={full ? "Your plan's limit is reached. Contact Ordo to raise it." : undefined}
    >
      {used.toLocaleString()} of {cap.toLocaleString()} {cap === 1 ? one : many} used
    </span>
  );
}
