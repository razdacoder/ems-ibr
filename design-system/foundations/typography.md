# Typography

## Typeface

**Outfit** (variable, 100–900) is used for everything: headings, body, numbers and the wordmark. In the app it comes from `@fontsource-variable/outfit`; outside it, use Google Fonts `Outfit`.

`font-serif` and `font-mono` are legacy class names that also resolve to Outfit. `font-mono` still does one thing: it turns on `tabular-nums`, so use it for counts, codes, IDs and timestamps. Body text has `rlig` and `calt` turned on.

## Scale and recipes

The app sets type with Tailwind arbitrary values. These are the recurring recipes, from largest to smallest:

| Role | Recipe | Notes |
|---|---|---|
| Display (landing) | `text-[2.75rem]`–`text-[3rem]`+, `leading-[1.02]`, `tracking-[-0.02em]` | Regular weight, `text-balance` |
| Page title (H1) | `text-[2.5rem] sm:text-[3rem] leading-[1.02–1.05] tracking-[-0.015em]–[-0.02em]` | Regular (400). Set large, not bold. |
| Section / stat | `text-[1.5rem]`–`text-[2rem]`, `tracking-tight` | Stats add `tabular-nums` |
| Card / dialog title | `text-lg font-semibold uppercase tracking-wider` | From `CardTitle` and `DialogTitle` |
| Lead / description | `text-[14.5px] leading-[1.65] text-muted-foreground max-w-2xl` | Under page titles |
| Body | `text-sm` (14px), `leading-relaxed` in descriptions | Default UI text |
| Nav item / meta | `text-[13px]`, `font-medium` | Sidebar, user block |
| Button | `text-xs font-semibold uppercase tracking-widest` | 12px, 0.1em |
| Label | `text-xs font-semibold uppercase tracking-wide` | Form labels |
| Table head | `text-xs font-medium uppercase tracking-wider text-muted-foreground` | |
| Eyebrow / overline | `font-mono text-[10px] uppercase tracking-[0.14em–0.18em] text-muted-foreground` | Most common type style in the app (≈120 uses) |
| Badge | `text-[0.625rem] font-semibold uppercase tracking-widest` | Text only: no fill or padding |
| Empty state | `text-[1.25rem] italic text-muted-foreground` | Under a "No records" eyebrow |
| Wordmark | `font-semibold tracking-[-0.03em] leading-none` | Only the logo is this tight |

## Rules

- Use **two weights** for structure: 400 for big type and 600 for small uppercase type. 500 is for nav and table text.
- **Uppercase always gets positive tracking**, from `tracking-wide` (0.025em) to `0.18em`; the smaller the text, the wider the tracking. **Large type always gets negative tracking.**
- Keep paragraphs to `max-w-2xl` (about 65ch).
- Prefer the eyebrow pattern (`Catalog · Students`) over breadcrumbs or extra heading levels.
