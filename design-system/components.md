# Components

The primitives live in [`frontend/src/components/ui/`](../frontend/src/components/ui/). They are shadcn **`base-sera`** style, built on `@base-ui/react` (Radix for form, label and toast), with variants from `class-variance-authority`. Every primitive sets `data-slot="<name>"`, so a parent can style its children by slot.

This page covers the design decisions behind each component. The code itself is the implementation.

## Button

Square, uppercase, `text-xs font-semibold tracking-widest`.

| Variant | Look | Use |
|---|---|---|
| `default` | Ink fill, Bone text, 80% on hover | Primary action |
| `brand` | Signal fill, near-black text | The one key CTA per view |
| `outline` | Hairline border, muted fill on hover | Secondary actions (most common: about 50 uses) |
| `secondary` | Mist fill | Low-emphasis filled |
| `ghost` | No chrome, muted on hover | Toolbars, icon buttons |
| `destructive` | `destructive/10` tint, red text | Delete or remove. Never a solid red fill. |
| `inverse` | Background-colour fill | On dark or brand panels |
| `link` | Underlined text | Inline |

Sizes: `xs` 28, `sm` 36, `default` 40, `lg` 44, plus `icon`, `icon-xs`, `icon-sm` and `icon-lg`. Focus shows `ring-2 ring-ring/30`; disabled is 50% opacity.

## Badge

**Text only**: no fill, border or padding. Set in 10px semibold uppercase with `tracking-widest`. The variants change only the colour: `default`, `secondary` (muted), `destructive`, `warning`, `outline`, `ghost`, `link`. Pair a badge with an icon (`size-3`) when it carries status.

## Section chip (PageHeader)

This is the one rounded, filled label: `rounded-full px-2.5 py-1`, 10px uppercase with `tracking-[0.18em]`, `--brand-soft` background and `--brand-strong` text, with a 4px dot in front.

## Input and Select trigger

Underline only: `border-transparent border-b-input bg-transparent px-0 h-10`. On focus the underline becomes `--ring`; when invalid it becomes `--destructive`. Placeholders are muted. A search field puts a 14px icon at `left-3` with `pl-9`. `PasswordInput` adds an eye toggle on the right.

## Label

`text-xs font-semibold uppercase tracking-wide`. When it sits next to a checkbox, radio or switch, it switches back to sentence-case 14px.

## Card

`bg-card shadow-sm ring-1 ring-foreground/5`, square, with `--card-spacing` padding (32px, or 20px for `size="sm"`). `CardTitle` is `text-lg semibold uppercase tracking-wider`. `CardAction` sits top-right in the header grid.

## Dialog and AlertDialog

Square, `p-6 gap-6`, `max-w-md` (AlertDialog `max-w-xs` on mobile). The overlay is black at 20% with a small blur. Open and close is a 100ms fade plus zoom-95. The close button is a ghost `icon-sm` button on a secondary fill at top-right. Footers are right-aligned and stack in reverse on mobile.

## Dropdown menu and Select content

A square popover with `p-1.5`. Items are `px-3 py-2 text-xs font-medium uppercase tracking-wider`, and focus fills them with `--accent`. Destructive items are red with a 10% tint on focus. Group labels are muted.

## Tabs

There are two list styles:
- `default`: a Mist rail, with the active tab on `bg-background`.
- `line`: transparent, with a 2px foreground underline on the active tab.

Triggers are `text-xs font-semibold uppercase tracking-wider`.

## Table

`text-sm`. Head cells are 48px tall, `text-xs uppercase tracking-wider` and muted. Cells are `p-3` and `whitespace-nowrap`. Rows have a bottom border and `muted/50` on hover. Per-row actions go in `RowActions` (right-aligned, `gap-1.5`) under a head cell with `w-px text-right`.

## Alert

Square, on `bg-card`, with a **2px left rule** (`after:w-0.5`) in the foreground colour, or in destructive red for `variant="destructive"`. Icons are 16px in their own grid column.

## Switch

A square track, 33×18px (`sm` 25×14). When on it fills with `--primary` (Ink, not green).

## Tooltip

Inverted colours (`bg-foreground text-background`), square, `text-xs px-3 py-1.5`, with a rotated-square arrow. The provider delay is 150ms.

## Skeleton

`animate-pulse bg-muted`, square. A list shows 6 rows at `h-10`.

## Composite patterns

- **PageHeader** (`components/layout/page-header.tsx`): the section chip, an H1 at 40–48px regular, a muted lead, optional meta, and actions aligned to the bottom-right. It has a hairline bottom border and `pb-8`.
- **ListShell** (`components/data-table/list-shell.tsx`): an eyebrow (`Catalog · X`), the header and an optional toolbar. Below that is a filter row with a search field, then a 12px-radius bordered card holding the table, a skeleton or an empty state, and a pagination footer on `muted/40`.
- **Empty state:** a centred eyebrow saying "No records", with an italic 20px muted sentence underneath.
- **Sidebar nav:** section headings are a 6px dot plus a 10px uppercase label. Items are 13px medium. The active item gets a 2px brand bar on the left. The user block is a round avatar, a name, and the role as an eyebrow.
- **BrandLockup:** the Ordo wordmark, a 1×20px hairline divider, then the institution logo on a white tile with `ring-1 ring-foreground/10`. See [`logo/README.md`](logo/README.md).
