/**
 * Hall seat layouts, mirroring ems/seating_rules.py.
 *
 * A layout is one string per row, "X" a seat and "." no seat (short row,
 * aisle, pillar). `null` means every cell of the rows × columns grid is a
 * seat. Seats are numbered 1..N over real seats only, row by row, so a full
 * rectangle numbers exactly as row * columns + col + 1.
 */

export type Align = "left" | "center" | "right";
export const ALIGNMENTS: Align[] = ["left", "center", "right"];

const SEAT = "X";
const GAP = ".";

/** How a hall numbers its seats, seen from the front (row 0 = front row).
 * Mirrors SEAT_ORDERS in ems/seating_rules.py. */
export type SeatOrder =
  | "rows"
  | "rows_rtl"
  | "snake"
  | "snake_rtl"
  | "columns"
  | "columns_snake";

export const SEAT_ORDERS: { value: SeatOrder; label: string }[] = [
  { value: "rows", label: "Row by row, left to right" },
  { value: "rows_rtl", label: "Row by row, right to left" },
  { value: "snake", label: "Snake, first row left to right" },
  { value: "snake_rtl", label: "Snake, first row right to left" },
  { value: "columns", label: "Column by column, front to back" },
  { value: "columns_snake", label: "Snake down and up the columns" },
];

/** Every cell of the grid in ``order``, as [row, col]. */
function sweep(rows: number, columns: number, order: SeatOrder): [number, number][] {
  const out: [number, number][] = [];
  const range = (n: number, forward: boolean) =>
    forward ? [...Array(n).keys()] : [...Array(n).keys()].reverse();
  if (order === "columns" || order === "columns_snake") {
    for (let c = 0; c < columns; c++) {
      for (const r of range(rows, order === "columns" || c % 2 === 0)) out.push([r, c]);
    }
    return out;
  }
  for (let r = 0; r < rows; r++) {
    const leftFirst =
      order === "rows_rtl" ? false
      : order === "snake" ? r % 2 === 0
      : order === "snake_rtl" ? r % 2 === 1
      : true;
    for (const c of range(columns, leftFirst)) out.push([r, c]);
  }
  return out;
}

/** One entry per grid cell, row by row as drawn: its seat number in the
 * hall's seat order, or null for no seat. */
export function seatNumberGrid(
  rows: number,
  columns: number,
  layout: string[] | null | undefined,
  order: SeatOrder = "rows",
): (number | null)[] {
  const cells: (number | null)[] = Array(rows * columns).fill(null);
  let next = 1;
  for (const [r, c] of sweep(rows, columns, order)) {
    if (!layout || layout[r]?.[c] === SEAT) cells[r * columns + c] = next++;
  }
  return cells;
}

export function maskFromRowSeats(counts: number[], align: Align): string[] {
  const cols = Math.max(0, ...counts);
  return counts.map((n) => {
    const pad = cols - n;
    const left = align === "left" ? 0 : align === "right" ? pad : Math.floor(pad / 2);
    return GAP.repeat(left) + SEAT.repeat(n) + GAP.repeat(pad - left);
  });
}
