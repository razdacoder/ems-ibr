import { useEffect, useState } from "react";
import { useBranding } from "@/api/system";
import { cn } from "@/lib/utils";

/**
 * Uploaded logos usually carry their own margin (a crest centred on a white
 * square), which would stack with the tile's padding and shrink the mark.
 * For Cloudinary-hosted logos, ask the CDN to trim that margin and serve a
 * right-sized copy; any other URL is used as-is.
 */
function tidyLogoUrl(url: string, px: number): string {
  const marker = "/image/upload/";
  if (!url.includes("res.cloudinary.com") || !url.includes(marker)) return url;
  const dpr = Math.ceil(px * 2);
  return url.replace(
    marker,
    `${marker}e_trim/c_limit,h_${dpr},f_auto,q_auto/`,
  );
}

/**
 * The configured institution logo, set on a white tile with a hairline frame.
 *
 * Uploaded logos arrive in every shape — transparent PNGs, JPGs on white,
 * dark marks that vanish on a dark canvas — so the tile gives each one the
 * light ground it was designed for. In light mode the tile melts into the
 * page; in dark mode it reads as a deliberate badge rather than a pasted
 * rectangle. Renders nothing until a logo is uploaded (or if it fails to
 * load), so it degrades cleanly on fresh installs.
 */
export function InstitutionLogo({
  size = 24,
  className,
  withDivider = false,
}: {
  /** Tile height in px; width follows the logo's aspect ratio. */
  size?: number;
  className?: string;
  /** Prefix a hairline rule, for sitting beside the Ordo wordmark. */
  withDivider?: boolean;
}) {
  const { data } = useBranding();
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [data?.logo_url]);

  if (!data?.logo_url || failed) return null;

  const pad = Math.max(2, Math.round(size * 0.14));
  const inner = size - pad * 2;
  const tile = (
    <span
      title={data.institution_name || undefined}
      className={cn(
        "inline-flex w-fit shrink-0 items-center justify-center bg-white ring-1 ring-foreground/10",
        className,
      )}
      style={{ height: size, padding: pad, maxWidth: size * 3 }}
    >
      <img
        src={tidyLogoUrl(data.logo_url, inner)}
        alt={data.institution_name || "Institution logo"}
        draggable={false}
        onError={() => setFailed(true)}
        className="w-auto max-w-full object-contain"
        style={{ height: inner }}
      />
    </span>
  );

  if (!withDivider) return tile;
  return (
    <span className="inline-flex items-center gap-3">
      <span aria-hidden className="h-5 w-px bg-border" />
      {tile}
    </span>
  );
}

/** The configured institution name as text. Renders nothing until one is set. */
export function InstitutionName({ className }: { className?: string }) {
  const { data } = useBranding();
  if (!data?.institution_name) return null;
  return <span className={className}>{data.institution_name}</span>;
}
