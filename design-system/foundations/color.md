# Color

The palette is neutral mauve-tinted greys (hue ≈ 322–326) plus one green accent. Values are authored in OKLCH; the hex values below are sRGB approximations for tools that need hex.

## Named colours

| Name | Value | Hex | Where |
|---|---|---|---|
| **Signal** | `#3fe06b` | `#3fe06b` | `--brand`: the accent, the logo seat, primary CTA fills |
| **Forest** | `#0e4d20` | `#0e4d20` | `--brand-strong` (light), `--brand-soft` (dark) |
| **Ink** | `oklch(0.145 0.008 326)` | `#0c090c` | Light text; dark background |
| **Ink 2 / Panel** | `oklch(0.212 0.019 322.12)` | `#1d161e` | Light `--primary`; dark cards |
| **Bone** | `oklch(1 0 0)` / `oklch(0.985 0 0)` | `#ffffff` / `#fafafa` | Light background; dark text |
| **Mist** | `oklch(0.96 0.003 325.6)` | `#f3f1f3` | Light secondary, muted, accent fills |
| **Hairline** | `oklch(0.922 0.005 325.62)` | `#e7e4e7` | Light border and input rule |
| **Mute** | `oklch(0.542 0.034 322.5)` | `#79697b` | Light secondary text |
| **Mute (dark)** | `oklch(0.711 0.019 323.02)` | `#a89ea9` | Dark secondary text, light focus ring |
| **Dusk** | `oklch(0.263 0.024 320.12)` | `#2a212c` | Dark secondary, muted, accent fills |
| **Alarm** | `oklch(0.577 0.245 27.3)` / `oklch(0.704 0.191 22.2)` | `#e7000b` / `#ff6467` | `--destructive` light / dark |

## Roles

| Token | Light | Dark | Use for |
|---|---|---|---|
| `--background` / `--foreground` | Bone / Ink | Ink / Bone | The page |
| `--card`, `--popover` | Bone | Panel | Raised surfaces |
| `--primary` / `-foreground` | Ink 2 / Bone | Hairline / Ink 2 | Default button, switch on. Ink, not green. |
| `--secondary`, `--muted`, `--accent` | Mist | Dusk | Hover fills, tab rails, skeletons, ghost hovers |
| `--muted-foreground` | Mute | Mute (dark) | Descriptions, eyebrows, table heads |
| `--border`, `--input` | Hairline | white 10% / 15% | Rules and field underlines |
| `--ring` | Mute (dark) | Mute | Focus outlines (used at 30–50% alpha) |
| `--destructive` | Alarm | Alarm (dark) | Errors and delete. Used as a 10–20% tint fill with full-colour text, not as a solid fill. |
| `--brand` / `-foreground` | Signal / near-black | same | `variant="brand"` buttons, logo seat, selection tint, live dots |
| `--brand-soft` | Signal 14% on bg | Forest | Tone-chip background |
| `--brand-strong` | Forest | Signal + 25% white | Tone-chip text, highlighted numbers |
| `--chart-1…5` | mauve ramp, light→deep | same | Data series (see below) |
| `--sidebar-*` | Off-white rail | Panel rail | App nav |

## Rules

- **Use green rarely.** Primary actions are **Ink** (`variant="default"`). Use `variant="brand"` (Signal fill) only for the single most important action on a page, such as Generate or Get started.
- **Text on Signal is always near-black** (`--brand-foreground: #0a0b0a`), never white.
- **Tones:** `PageHeader tone=…` and the `--accent-<tone>` slots all show the same soft-green chip. Write the meaning in the label.
- **Errors** use `--destructive`, as a tint fill (`bg-destructive/10 text-destructive`) or a left rule (`Alert variant="destructive"`).
- **Selection:** `::selection` uses Signal at 28% alpha.
- **Charts:** by default the ramp is neutral, so the series tell values apart through lightness only. When an institution colour is set, `--chart-1…5` become an L 0.78 → 0.30 ramp at the brand hue.

## Institution brand override

`frontend/src/lib/brand.tsx` converts the configured hex to OKLCH. It keeps the hue, clamps the chroma to 0.08–0.26, and writes inline custom properties on `<html>`:

| Var | Light L / C | Dark L / C |
|---|---|---|
| `--brand` | 0.55 / chroma | 0.70 / ≤0.20 |
| `--brand-foreground` | 0.99 / 0.005 | 0.155 / 0.012 |
| `--brand-soft` | 0.95 / 0.045 | 0.32 / 0.10 |
| `--brand-strong` | 0.42 / ≤0.22 | 0.84 / ≤0.16 |

When a custom brand is set, the text on brand fills is light in light mode. Signal's near-black only applies to the default.
