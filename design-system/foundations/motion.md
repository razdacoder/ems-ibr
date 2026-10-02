# Motion

**Easing:** `cubic-bezier(0.16, 1, 0.3, 1)` (expo-out) is used everywhere: things arrive quickly and settle slowly.

| Duration | Used for |
|---|---|
| 100ms | Popover, menu and dialog open and close (`tw-animate-css` fade, zoom-95 and slide-2) |
| 320ms | Hover underline draw |
| 600–700ms | Fade-in, fade-up and scroll reveal |
| 900–1400ms | Bar grow, progress fill and SVG line draw |
| 2.4s loop | `animate-pulse-soft` on live and status dots |
| 38s loop | Logo marquee (landing) |

## Primitives ([`tokens/motion.css`](../tokens/motion.css))

| Hook | Effect | Parameters |
|---|---|---|
| `[data-reveal]` | Fade in and rise 12px when scrolled into view | `--reveal-delay` |
| `[data-draw]` | Draws an SVG stroke | `--draw-len` (match the `pathLength`) |
| `[data-grow]` | Height grows from 0 | `--grow-h` |
| `[data-fill]` | Width fills from 0 | `--fill-w` |
| `.animate-fade-up` / `.animate-fade-in` | Plays once on mount | `--anim-delay` |
| `.animate-pulse-soft` | Breathing scale and opacity | — |
| `.draw-underline` | Underline that wipes in on hover (or on hover of a `.group` parent) | — |
| `.marquee-track` | Endless horizontal scroll (duplicate the content) | — |

The scroll hooks need `.is-visible` added when the element intersects the viewport (`useReveal()` in `frontend/src/lib/use-reveal.ts`, rootMargin −8% bottom). To stagger siblings, step `--reveal-delay` by about 60–80ms.

**Reduced motion:** every primitive above jumps straight to its end state.

Buttons nudge down 1px on press (`active:translate-y-px`).
