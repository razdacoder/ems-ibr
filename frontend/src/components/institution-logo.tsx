import { useBranding } from "@/api/system";
import { cn } from "@/lib/utils";

/**
 * The configured institution logo, sized to sit beside the Ordo mark.
 * Renders nothing until an institution logo has been uploaded, so it degrades
 * cleanly on fresh installs.
 */
export function InstitutionLogo({
  size = 24,
  className,
}: {
  size?: number;
  className?: string;
}) {
  const { data } = useBranding();
  if (!data?.logo_url) return null;
  return (
    <img
      src={data.logo_url}
      alt={data.institution_name || "Institution logo"}
      className={cn("shrink-0 object-contain", className)}
      style={{ height: size, width: "auto", maxWidth: size * 2.5 }}
    />
  );
}

/** The configured institution name as text. Renders nothing until one is set. */
export function InstitutionName({ className }: { className?: string }) {
  const { data } = useBranding();
  if (!data?.institution_name) return null;
  return <span className={className}>{data.institution_name}</span>;
}
