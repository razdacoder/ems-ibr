/**
 * TanStack Router parses search values as JSON where it can, so
 * `?hall_id=12` arrives as the number 12. Pages here treat search params as
 * strings; normalise them in each route's validateSearch.
 */
export function str(value: unknown): string | undefined {
  if (value === undefined || value === null || value === "") return undefined;
  return String(value);
}
