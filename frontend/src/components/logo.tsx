import { cn } from "@/lib/utils";

/**
 * Ordo mark — a 5x5 grid with five cells lit: four in the neutral
 * foreground tone, one in Signal green. Reads as "order found inside
 * scattered data" — the brand's whole thesis in one glyph.
 */
const GRID_SIZE = 5;
const CELL = 6;
const GAP = 2;
const STEP = CELL + GAP;
const ORIGIN = 1;
const VIEWBOX = ORIGIN * 2 + GRID_SIZE * CELL + (GRID_SIZE - 1) * GAP;

/** (row, col) cells lit in the neutral tone. */
const LIT_CELLS: Array<[number, number]> = [
  [0, 1],
  [2, 0],
  [3, 4],
  [4, 2],
];
/** (row, col) cell lit in Signal green — the mark's focal point. */
const SIGNAL_CELL: [number, number] = [1, 3];

function cellRect(row: number, col: number) {
  return {
    x: ORIGIN + col * STEP,
    y: ORIGIN + row * STEP,
    width: CELL,
    height: CELL,
    rx: 1.6,
  };
}

export function Logo({
  className,
  size = 16,
}: {
  className?: string;
  size?: number;
}) {
  const cells = Array.from({ length: GRID_SIZE * GRID_SIZE }, (_, i) => [
    Math.floor(i / GRID_SIZE),
    i % GRID_SIZE,
  ]) as Array<[number, number]>;

  return (
    <svg
      aria-hidden
      viewBox={`0 0 ${VIEWBOX} ${VIEWBOX}`}
      width={size}
      height={size}
      className={cn("shrink-0", className)}
    >
      {cells.map(([row, col]) => {
        const isSignal = row === SIGNAL_CELL[0] && col === SIGNAL_CELL[1];
        const isLit = LIT_CELLS.some(([r, c]) => r === row && c === col);
        const rect = cellRect(row, col);
        if (isSignal) {
          return (
            <rect key={`${row}-${col}`} {...rect} fill="var(--brand)" />
          );
        }
        if (isLit) {
          return (
            <rect
              key={`${row}-${col}`}
              {...rect}
              fill="currentColor"
              opacity="0.55"
            />
          );
        }
        return (
          <rect
            key={`${row}-${col}`}
            {...rect}
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
            opacity="0.18"
          />
        );
      })}
    </svg>
  );
}

/**
 * Wordmark + mark, the standard header brand-line. Use this anywhere the
 * literal "Ordo" string appears next to the logo.
 */
export function Wordmark({
  className,
  size = "md",
}: {
  className?: string;
  size?: "sm" | "md" | "lg";
}) {
  const px = size === "lg" ? 22 : size === "sm" ? 14 : 18;
  const text =
    size === "lg"
      ? "text-[1.5rem]"
      : size === "sm"
        ? "text-[1.125rem]"
        : "text-[1.25rem]";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 font-serif tracking-tight",
        text,
        className,
      )}
    >
      <Logo size={px} />
      Ordo
    </span>
  );
}
