import { Badge } from "@/components/ui/badge";

/** Marks a course seated under the relaxed rule (spec 0002): too big for one
 * period, so only side, front and back neighbours of the same course are
 * blocked. Invigilators should watch the diagonals. */
export function RelaxedSeatingBadge() {
  return (
    <Badge
      variant="warning"
      title="Too big for one period under the strict rule. Students of this course may sit diagonally next to each other, so watch the diagonals."
    >
      Relaxed seating
    </Badge>
  );
}
