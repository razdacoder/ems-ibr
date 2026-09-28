/**
 * Display formatting for uploaded records. Spreadsheet imports arrive with
 * shouty capitals, stray whitespace and pandas' "nan" for empty cells, so
 * every name, email and course title goes through these before it hits the UI.
 */

/** Shown wherever a value is missing. */
export const EMPTY = "-";

const BLANK_TOKENS = new Set(["", "nan", "none", "null", "undefined", "n/a", "na", "-"]);

/** True for null/undefined, empty strings and spreadsheet placeholders like "nan". */
export function isBlank(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === "number") return Number.isNaN(value);
  return BLANK_TOKENS.has(String(value).trim().toLowerCase());
}

/** The value as trimmed text, or EMPTY when it's blank. */
export function orEmpty(value: unknown): string {
  return isBlank(value) ? EMPTY : String(value).trim().replace(/\s+/g, " ");
}

/** Capitalise one word, keeping hyphen/apostrophe parts ("o'neil-ade" → "O'Neil-Ade"). */
function capitalise(word: string): string {
  return word
    .toLowerCase()
    .replace(/(^|[-'’])(\p{L})/gu, (_, sep: string, ch: string) => sep + ch.toUpperCase());
}

/** A person's name in Title Case, or EMPTY when every part is blank. */
export function formatName(...parts: Array<string | null | undefined>): string {
  const words = parts
    .filter((p) => !isBlank(p))
    .flatMap((p) => String(p).trim().split(/\s+/))
    .map(capitalise);
  return words.length ? words.join(" ") : EMPTY;
}

/** Initials for avatar chips, from the non-blank name parts. */
export function initials(...parts: Array<string | null | undefined>): string {
  return parts
    .filter((p) => !isBlank(p))
    .map((p) => String(p).trim()[0]?.toUpperCase() ?? "")
    .join("");
}

/** Emails are case-insensitive; show them lowercased and trimmed. */
export function formatEmail(value: string | null | undefined): string {
  return isBlank(value) ? EMPTY : String(value).trim().toLowerCase();
}

const MINOR_WORDS = new Set([
  "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the", "to", "with",
]);
const ROMAN = /^(i|ii|iii|iv|v|vi|vii|viii|ix|x)$/i;

/**
 * Course and document titles in Title Case: minor words stay lowercase
 * (except first), Roman numerals stay upper ("Mathematics II"), and tokens
 * with digits are left alone ("Phase 2a").
 */
export function formatTitle(value: string | null | undefined): string {
  if (isBlank(value)) return EMPTY;
  return String(value)
    .trim()
    .split(/\s+/)
    .map((word, i) => {
      if (/\d/.test(word)) return word;
      if (ROMAN.test(word)) return word.toUpperCase();
      if (i > 0 && MINOR_WORDS.has(word.toLowerCase())) return word.toLowerCase();
      return capitalise(word);
    })
    .join(" ");
}
