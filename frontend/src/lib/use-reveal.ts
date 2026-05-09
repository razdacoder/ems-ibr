import { useEffect } from "react";

/**
 * Reveal-on-scroll hook.
 *
 * Looks for any motion-tagged element in the DOM and adds `is-visible` once it
 * enters the viewport. Recognised attributes:
 *
 *   data-reveal  — fade + translate up (default scroll-in)
 *   data-draw    — SVG path stroke-dashoffset animation
 *   data-grow    — height grows from 0 → var(--grow-h)
 *   data-fill    — width fills from 0 → var(--fill-w)
 *
 * Use the inline CSS variable `--reveal-delay` to stagger siblings. Above-the-
 * fold elements reveal on mount because they're already intersecting.
 */
export function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll<HTMLElement>(
      "[data-reveal], [data-draw], [data-grow], [data-fill]",
    );
    if (!("IntersectionObserver" in window)) {
      els.forEach((el) => el.classList.add("is-visible"));
      return;
    }
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add("is-visible");
            obs.unobserve(e.target);
          }
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.05 },
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  });
}
