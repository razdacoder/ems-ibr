import type { ReactNode } from "react";

/**
 * Per-row table actions: one line, right-aligned, never wrapping. Pair with
 * an Actions header of `ACTIONS_HEAD_CLASS` so the column shrinks to fit.
 */
export function RowActions({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-nowrap items-center justify-end gap-1.5">
      {children}
    </div>
  );
}

export const ACTIONS_HEAD_CLASS = "w-px text-right";
