# Ordo design system

This is the visual language of the Ordo frontend, taken out of `frontend/` so it can be reused in other places: Django templates, generated documents, a marketing site, or a new app. It describes what the code does today, not a redesign.

**Source of truth:** [`frontend/src/index.css`](../frontend/src/index.css) and [`frontend/src/components/ui/`](../frontend/src/components/ui/). If you change a token there, change it here as well.

Open [`preview.html`](preview.html) in a browser to see everything on one page, in light and dark.

## The idea in one line

Ink text on a Bone canvas, square controls, small uppercase labels with wide letter-spacing, and a single accent colour, **Signal green**, used sparingly.

## Principles

1. **One accent, used for meaning.** Signal green (`--brand`) is the only colour that isn't neutral. All tone slots (`--accent-iris`, `-amber`, `-coral`, …) resolve to the same green pair. A status is shown by its label and icon, not by its colour. The one exception is `--destructive`, the red used for errors.
2. **Square controls, rounded containers.** Buttons, inputs, menus, dialogs, tabs and switches all use `rounded-none`. Page-level surfaces (list bodies, feature tiles) are 12–14px. Only dots, avatars and the section chip are fully round.
3. **Uppercase micro-type for UI, large and light type for content.** Controls and labels are 10–12px, uppercase, semibold, with wide tracking. Page titles are 40–48px, regular weight, with tight negative tracking. Little sits in between.
4. **Underlined fields, not boxes.** Inputs and selects have no box around them: just a bottom rule that darkens to `--ring` on focus.
5. **Quiet elevation.** Cards use `ring-1 ring-foreground/5 shadow-sm`; popovers use `ring-foreground/10 shadow-md`. The only coloured shadow is `.shadow-brand`.
6. **Motion that settles.** Everything eases out on `cubic-bezier(0.16, 1, 0.3, 1)` and is turned off under `prefers-reduced-motion`.
7. **Institutions can recolour it.** An institution can set its own brand colour. `lib/brand.tsx` keeps Ordo's lightness and chroma scale and swaps in only the hue, so `--brand*` and `--chart-*` change at runtime. Always reference these colours by token, never by hex.

## Contents

| Path | What it is |
|---|---|
| [`tokens/tokens.css`](tokens/tokens.css) | All tokens as plain CSS custom properties, light and dark. Needs no framework. |
| [`tokens/tailwind-theme.css`](tokens/tailwind-theme.css) | Tailwind v4 `@theme` bridge and base layer, matching the app. |
| [`tokens/motion.css`](tokens/motion.css) | Reveal, draw, grow and fill on scroll, fade-up, pulse and draw-underline. |
| [`tokens/tokens.json`](tokens/tokens.json) | The same tokens as JSON, for tooling (Figma, Style Dictionary, Python). |
| [`foundations/color.md`](foundations/color.md) | Palette, roles, hex equivalents, brand override. |
| [`foundations/typography.md`](foundations/typography.md) | Typeface, type scale, text recipes. |
| [`foundations/layout.md`](foundations/layout.md) | Shape, spacing, elevation, page structure, icons. |
| [`foundations/motion.md`](foundations/motion.md) | Easing, durations, primitives. |
| [`components.md`](components.md) | Component inventory, variants, and the class recipes behind them. |
| [`logo/`](logo/) | Ordo mark and wordmark (SVG, outlined), favicons, usage rules. |
| [`preview.html`](preview.html) | Visual specimen of everything above. |

## Quick start

**Plain HTML or Django templates**

```html
<link rel="stylesheet" href="design-system/tokens/tokens.css">
<link rel="stylesheet" href="design-system/tokens/motion.css">
<body style="background:var(--background);color:var(--foreground);font-family:var(--font-sans)">
```

**New Tailwind v4 + shadcn project.** Import `tokens.css`, `tailwind-theme.css` and `motion.css` in that order. Then copy the primitives from `frontend/src/components/ui/`. They are shadcn's `base-sera` style on `@base-ui/react`, with the Ordo overrides already applied.

## Known inconsistencies

These were found while extracting the system. The docs describe the intended rule; the code doesn't follow it yet.

- **Light `--brand-soft` renders pale pink, not pale green.** It is defined as `color-mix(in oklch, var(--brand) 14%, var(--background))`, and `--background` is `oklch(1 0 0)`. The `0` there is an explicit hue, not `none`, so the mix interpolates the hue from 142° to 0°. This affects every light-mode section chip and tone fill in the app. Fix: write the background as `oklch(1 0 none)`, or mix `in srgb`.
- **Red and amber tones render green.** `--accent-red-fg` and `--accent-yellow-fg` alias to the brand pair. They are still used where an error or warning colour is clearly meant: the Settings danger zone, over-capacity counts in allocation, hall validation text, failed job status, and distribution load bars. Those places should use `--destructive` (or a label and icon) instead.
- **Dark `--sidebar-primary` is a stray blue** (`oklch(0.488 0.243 264)`) left over from the shadcn default. It is unused today but off-system.
- **The `--chart-*` comment says "Signal green shades"**, but the defaults are neutral mauve. They only turn into brand-hue shades when an institution colour is set.
- **Toast** still uses the older shadcn recipe (`rounded-md`, `red-300` and similar), not the square, token-only style.
- **The favicon's ink** is `#251b28`, but the Ink token is `#0c090c`. The files in `logo/` use the token.
- **Unused fonts:** `@fontsource-variable/bodoni-moda` and `@fontsource/ibm-plex-mono` are installed but never imported. `font-serif` and `font-mono` both map to Outfit.
