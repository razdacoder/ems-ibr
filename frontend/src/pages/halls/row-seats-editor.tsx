import { useRef, useState } from "react";
import { Copy, Minus, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const DEFAULT_SEATS = 10;

/**
 * Seats per row, front row first, as one editable line per row.
 *
 * Enter in a row adds a row below with the same count and moves to it;
 * the up and down arrows move between rows. The bar on top adds several
 * equal rows at once, the common case for a hall's back block.
 */
export function RowSeatsEditor({
  value,
  onChange,
}: {
  value: number[];
  onChange: (next: number[]) => void;
}) {
  const [bulkRows, setBulkRows] = useState(5);
  const [bulkSeats, setBulkSeats] = useState(DEFAULT_SEATS);
  const list = useRef<HTMLDivElement>(null);

  const focusRow = (index: number) =>
    requestAnimationFrame(() =>
      list.current
        ?.querySelector<HTMLInputElement>(`input[data-row="${index}"]`)
        ?.select(),
    );

  const set = (index: number, seats: number) =>
    onChange(value.map((n, i) => (i === index ? Math.max(0, seats) : n)));
  const insertAfter = (index: number, seats: number) => {
    onChange([...value.slice(0, index + 1), seats, ...value.slice(index + 1)]);
    focusRow(index + 1);
  };
  const remove = (index: number) => onChange(value.filter((_, i) => i !== index));
  const addBulk = () => {
    if (bulkRows > 0) onChange([...value, ...Array(bulkRows).fill(Math.max(0, bulkSeats))]);
  };

  const total = value.reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2 border border-dashed border-border p-3">
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Add
          <Input
            type="number"
            min={1}
            value={bulkRows}
            onChange={(e) => setBulkRows(Math.max(0, Number(e.target.value) || 0))}
            className="h-8 w-16 font-mono"
            aria-label="Number of rows to add"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          rows of
          <Input
            type="number"
            min={0}
            value={bulkSeats}
            onChange={(e) => setBulkSeats(Math.max(0, Number(e.target.value) || 0))}
            className="h-8 w-16 font-mono"
            aria-label="Seats in each added row"
          />
        </label>
        <span className="pb-2 text-xs text-muted-foreground">seats</span>
        <Button type="button" size="sm" variant="outline" onClick={addBulk}>
          Add rows
        </Button>
      </div>

      <div className="flex items-baseline justify-between">
        <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
          {value.length} rows · {total} seats · front row first
        </p>
        {value.length > 0 && (
          <Button type="button" size="xs" variant="ghost" onClick={() => onChange([])}>
            Clear all
          </Button>
        )}
      </div>

      <div ref={list} className="divide-y divide-border border border-border">
        {value.length === 0 && (
          <p className="p-4 text-center text-sm text-muted-foreground">
            No rows yet. Add them above, or one at a time below.
          </p>
        )}
        {value.map((seats, i) => (
          <div key={i} className="flex items-center gap-2 px-3 py-1.5">
            <span className="w-14 font-mono text-[11px] text-muted-foreground">
              Row {i + 1}
            </span>
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              onClick={() => set(i, seats - 1)}
              disabled={seats <= 0}
              aria-label={`One seat fewer in row ${i + 1}`}
            >
              <Minus />
            </Button>
            <Input
              data-row={i}
              type="number"
              min={0}
              value={seats}
              onChange={(e) => set(i, Number(e.target.value) || 0)}
              onFocus={(e) => e.target.select()}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault(); // not a form submit
                  insertAfter(i, seats);
                } else if (e.key === "ArrowDown" && i < value.length - 1) {
                  e.preventDefault();
                  focusRow(i + 1);
                } else if (e.key === "ArrowUp" && i > 0) {
                  e.preventDefault();
                  focusRow(i - 1);
                }
              }}
              className="h-8 w-16 text-center font-mono"
              aria-label={`Seats in row ${i + 1}`}
            />
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              onClick={() => set(i, seats + 1)}
              aria-label={`One more seat in row ${i + 1}`}
            >
              <Plus />
            </Button>
            <span className="text-xs text-muted-foreground">seats</span>
            <div className="ml-auto flex gap-1">
              <Button
                type="button"
                size="icon-sm"
                variant="ghost"
                onClick={() => insertAfter(i, seats)}
                title="Duplicate this row"
                aria-label={`Duplicate row ${i + 1}`}
              >
                <Copy />
              </Button>
              <Button
                type="button"
                size="icon-sm"
                variant="ghost"
                onClick={() => remove(i)}
                title="Remove this row"
                aria-label={`Remove row ${i + 1}`}
              >
                <Trash2 />
              </Button>
            </div>
          </div>
        ))}
      </div>

      <Button
        type="button"
        size="sm"
        variant="outline"
        className="w-full"
        onClick={() => insertAfter(value.length - 1, value.at(-1) ?? DEFAULT_SEATS)}
      >
        <Plus data-icon="inline-start" /> Add row
      </Button>
      <p className="text-xs text-muted-foreground">
        Tip: press Enter in a row to add another with the same seats; use ↑ ↓
        to move between rows.
      </p>
    </div>
  );
}
