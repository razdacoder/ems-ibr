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

- **Amber tones still render green.** `--accent-yellow*` / `--accent-amber*` alias to the brand pair, and that's deliberate under principle 1: queued, pending and near-capacity states are told apart by label and icon. If a real warning colour is ever wanted, it needs adding as a token, not borrowed from a palette.
- **Raster favicons** (`favicon-32.png`, `apple-touch-icon.png`) still carry the old ink `#251b28`; re-export them from `favicon.svg`.

Resolved (October 2026): light `--brand-soft` drifting pink (Bone is now `oklch(1 0 none)`), the red tone rendering green (`--accent-red*` now resolve to `--destructive`), the stray blue dark `--sidebar-primary` (now `--primary`), the `--chart-*` comment, the Toast recipe (now square and token-only), the favicon SVG ink (now the Ink token), and the unused Bodoni Moda / IBM Plex Mono packages (removed).
