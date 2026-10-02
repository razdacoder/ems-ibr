# Shape, spacing, elevation and layout

## Shape

| Element | Radius |
|---|---|
| Buttons, inputs, selects, menus, dialogs, tabs, switches, tooltips, alerts | `rounded-none` (0) |
| Small inline boxes (seat cells, swatches) | `rounded-[4px]` |
| Page body containers (list shell, panels) | `rounded-[12px]` |
| Marketing tiles and feature cards | `rounded-[14px]` |
| Section chip, avatar, status dot | `rounded-full` |

`--radius` is 10px, and the `rounded-sm`…`rounded-4xl` scale derives from it. The primitives override it to 0, so in practice the radius scale is only used on page-level surfaces.

## Spacing

The base unit is 4px, from Tailwind.

- Space between page sections: `space-y-10` (40px).
- Page header: `pb-8` with a bottom `border`, and `gap-6` between the title block and the actions.
- Card padding is `--card-spacing`: 32px by default, 20px for `size="sm"`.
- Dialogs use `p-6 gap-6`. Menus use `p-1.5` with items at `px-3 py-2`.
- Table cells use `p-3` with a 48px head row.
- Page width is `max-w-7xl` for marketing; app pages fill the content column.

## Control heights

| Size | Button | Icon button | Input / select |
|---|---|---|---|
| xs | 28px (`h-7`) | 28 | — |
| sm | 36px (`h-9`) | 36 | 36 (`size="sm"`) |
| default | 40px (`h-10`) | 40 | 40 |
| lg | 44px (`h-11`) | 44 | — |

## Elevation

| Level | Recipe |
|---|---|
| Flat | `border border-border` |
| Card | `shadow-sm ring-1 ring-foreground/5` |
| Popover, menu, dialog | `shadow-md ring-1 ring-foreground/10` |
| Modal overlay | `bg-black/20 backdrop-blur-sm` |
| Brand lift | `.shadow-brand`: `0 12px 28px -16px` Signal at 55% |

## Page anatomy (app)

```
┌ sidebar (--sidebar) ─┬─ content ───────────────────────────────────┐
│ Wordmark + inst. logo│ EYEBROW · SECTION                    [acts] │
│                      │ Page title (40–48px, regular)               │
│ ● SECTION LABEL      │ Lead paragraph, muted, max-w-2xl            │
│ │ Nav item           │ ─────────────────────────────────────────── │
│ ▌ Active item        │ ALL ITEMS  [filters]           [search___]  │
│                      │ ┌ 12px card ─────────────────────────────┐  │
│ ──────────────────── │ │ TABLE HEAD                             │  │
│ (avatar) Name        │ │ rows…                                  │  │
│          ROLE        │ ├────────────────────────── muted/40 ────┤  │
└──────────────────────┴─┴ Showing 1–20 of 340   ‹ Prev  Next ›   ┴──┘
```

The active nav item is marked with a 2px brand-coloured bar on the left edge.

## Icons

Icons come from **lucide-react**, drawn at `strokeWidth={2}`, at `size-3.5` (14px) inside controls and `size-4` elsewhere. Icons inside buttons use `data-icon="inline-start|inline-end"` so the button tightens its padding on that side.
