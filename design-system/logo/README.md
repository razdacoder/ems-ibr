# Ordo logo

The mark is a square **O** with its top-right corner lifted out as a single **Signal-green seat**. It reads as the O of Ordo and as a seat being placed, which is what the product does. It is drawn on a 24-unit grid, so every edge lands on a whole pixel at 16, 24 and 32px.

```
Mark geometry (24 × 24)
  O:    M1 1 H13 V6 H6 V18 H18 V11 H23 V23 H1 Z   (5-unit stroke)
  Seat: rect x=15 y=1 w=8 h=8                     (2-unit gap to the O)
```

## Files

| File | Use |
|---|---|
| `ordo-mark.svg` | Ink mark with Signal seat, on light backgrounds |
| `ordo-mark-reversed.svg` | Bone mark with Signal seat, on dark backgrounds |
| `ordo-mark-auto.svg` | Switches with `prefers-color-scheme`. Use it as a favicon or wherever the theme is unknown. |
| `ordo-mark-mono-black.svg` / `-mono-white.svg` | Single colour, for print, fax, embossing, or when the green can't be reproduced |
| `ordo-wordmark.svg` | Mark plus "Ordo", on light backgrounds |
| `ordo-wordmark-reversed.svg` | Mark plus "Ordo", on dark backgrounds |
| `ordo-wordmark-mono-black.svg` / `-mono-white.svg` | Single-colour wordmark |
| `favicon.svg`, `favicon-32.png`, `apple-touch-icon.png` | Copies of the files in `frontend/public/`, as shipped |

The wordmark text is **outlined** (Outfit SemiBold 600, tracking −0.03em), so it doesn't need the font installed. Its proportions match the app's `<Wordmark>`: the mark is the same height as the font size, with a gap of 0.44× the font size.

## In the app

Use the React components in [`frontend/src/components/logo.tsx`](../../frontend/src/components/logo.tsx) rather than these files:

- `<Logo size={16} />` draws the mark. It uses `currentColor` for the O and `var(--brand)` for the seat, so **the seat follows an institution's brand colour** when one is set.
- `<Wordmark size="sm|md|lg" />` uses mark sizes 16, 18 or 24px with text at the same size.
- `<BrandLockup />` shows the wordmark, a hairline divider, then the institution's uploaded logo.

## Rules

- **Clear space:** at least the seat's width (⅓ of the mark height) on every side.
- **Minimum size:** 16px for the mark and 72px wide for the wordmark. Keep `shape-rendering="crispEdges"` at small sizes.
- **Seat colour:** Signal `#3fe06b` or the active `--brand`, nothing else. In mono versions the seat is the same colour as the O.
- **Don't** round the corners, add a stroke, put the seat in another corner, rotate it, set "Ordo" in another font, or place the full-colour mark on Signal green (use mono there).
- **Co-branding:** Ordo comes first, then a hairline divider, then the institution logo on a white tile with 14% padding. The tile keeps institution logos legible in dark mode. The institution logo is uploaded data (Settings → Branding), not part of this kit.
