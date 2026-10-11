import * as React from "react"
import { format, isValid, parse } from "date-fns"
import { CalendarIcon, XIcon } from "lucide-react"
import { cn } from "cn"

import { Calendar } from "@/components/ui/calendar"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

// Values use the native input wire formats so forms and API payloads don't
// change: "yyyy-MM-dd" for dates, "yyyy-MM-dd'T'HH:mm" (datetime-local) with
// time. An empty string means no value.
const DATE_FORMAT = "yyyy-MM-dd"
const DATETIME_FORMAT = "yyyy-MM-dd'T'HH:mm"

function parseValue(value: string | null | undefined): Date | undefined {
  if (!value) return undefined
  const fmt = value.includes("T") ? DATETIME_FORMAT : DATE_FORMAT
  // Tolerate seconds or a zone suffix from the API: keep the minute part only.
  const parsed = parse(value.slice(0, fmt === DATE_FORMAT ? 10 : 16), fmt, new Date())
  return isValid(parsed) ? parsed : undefined
}

/** Year span the month/year dropdowns offer. */
const START_MONTH = new Date(new Date().getFullYear() - 100, 0)
const END_MONTH = new Date(new Date().getFullYear() + 20, 11)

interface DatePickerProps
  extends Omit<React.ComponentProps<"button">, "value" | "onChange" | "defaultValue"> {
  value: string | null | undefined
  onChange: (value: string) => void
  /** Also pick a time; the value becomes "yyyy-MM-ddTHH:mm". */
  withTime?: boolean
  /** Earliest / latest selectable day, in the same format as `value`. */
  min?: string
  max?: string
  placeholder?: string
  /** Show a clear button when a value is set. */
  clearable?: boolean
}

/** Shadcn calendar in a popover, styled like `Input`. Drop-in for a field. */
const DatePicker = React.forwardRef<HTMLButtonElement, DatePickerProps>(function DatePicker(
  {
    value,
    onChange,
    withTime = false,
    min,
    max,
    placeholder,
    clearable = false,
    disabled,
    className,
    ...props
  },
  ref,
) {
  const [open, setOpen] = React.useState(false)
  const timeId = React.useId()
  const selected = parseValue(value)
  const minDate = parseValue(min)
  const maxDate = parseValue(max)
  const time = selected ? format(selected, "HH:mm") : "09:00"

  const emit = (day: Date | undefined, hhmm = time) => {
    if (!day) return onChange("")
    if (!withTime) return onChange(format(day, DATE_FORMAT))
    const [h, m] = hhmm.split(":").map(Number)
    const next = new Date(day)
    next.setHours(h || 0, m || 0, 0, 0)
    onChange(format(next, DATETIME_FORMAT))
  }

  const disabledDays = [
    ...(minDate ? [{ before: minDate }] : []),
    ...(maxDate ? [{ after: maxDate }] : []),
  ]

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <div className="relative w-full">
        <PopoverTrigger
          ref={ref}
          type="button"
          disabled={disabled}
          data-slot="date-picker"
          data-empty={!selected || undefined}
          className={cn(
            "flex h-10 w-full min-w-0 items-center gap-2 border border-transparent border-b-input bg-transparent px-0 py-1 text-left text-base transition-[color,border-color] outline-none focus-visible:border-b-ring disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-b-destructive data-empty:text-muted-foreground md:text-sm dark:aria-invalid:border-b-destructive/50",
            clearable && selected && "pr-7",
            className,
          )}
          {...props}
        >
          <CalendarIcon className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
          <span className="truncate">
            {selected
              ? format(selected, withTime ? "d MMM yyyy, HH:mm" : "d MMM yyyy")
              : (placeholder ?? (withTime ? "Pick a date and time" : "Pick a date"))}
          </span>
        </PopoverTrigger>
        {clearable && selected && !disabled && (
          <button
            type="button"
            aria-label="Clear date"
            onClick={() => onChange("")}
            className="absolute top-1/2 right-0 grid size-6 -translate-y-1/2 place-items-center text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/30"
          >
            <XIcon className="size-3.5" />
          </button>
        )}
      </div>
      <PopoverContent align="start" className="w-auto gap-0 p-0">
        <Calendar
          mode="single"
          captionLayout="dropdown"
          startMonth={START_MONTH}
          endMonth={END_MONTH}
          selected={selected}
          defaultMonth={selected ?? minDate}
          disabled={disabledDays}
          onSelect={(day) => {
            emit(day)
            if (!withTime) setOpen(false)
          }}
          autoFocus
        />
        {withTime && (
          <div className="flex items-center gap-3 border-t border-[color:var(--border)] px-3 py-2">
            <label htmlFor={timeId} className="text-[13px] text-muted-foreground">
              Time
            </label>
            <Input
              id={timeId}
              type="time"
              value={time}
              disabled={!selected}
              onChange={(e) => emit(selected, e.target.value)}
              className="h-8 flex-1 appearance-none bg-transparent [&::-webkit-calendar-picker-indicator]:hidden"
            />
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
})

export { DatePicker }
export type { DatePickerProps }
