"""Hall Directory (hall summary) and VISA data builders.

Two per-slot exam documents:

* **Hall Directory / Hall Summary** — for a (date, period), one row per
  (hall, class): hall name, class name, number of students, and the matric
  number range. Sourced from generated seat allocation (``SeatArrangement``).
* **VISA** — the set of classes being examined that (date, period), rendered
  as short codes (see :func:`derive_visa_code`).

Both can be scoped to a single slot, a calendar week (Mon-Sat), or the whole
exam duration.
"""

from datetime import timedelta

from ems.models import Class, SeatArrangement, TimeTable

# Qualifier -> VISA prefix letter. ND has no prefix; Pre-ND -> P; Higher ND -> H.
_QUALIFIER_PREFIX = {"ND": "", "PND": "P", "HND": "H"}


def derive_visa_code(name: str) -> str:
    """Convert a stored class name to its VISA short code.

    ``PROGRAM[-SPEC] QUALIFIER YEAR`` -> ``{prefix}PROGRAM YEAR[_SPEC]``::

        "AC ND II"        -> "AC II"
        "AC PND II"       -> "PAC II"
        "AC HND II"       -> "HAC II"
        "ABET-SW HND II"  -> "HABET II_SW"

    Falls back to the trimmed name when no known qualifier is present.
    """
    if not name:
        return ""
    tokens = name.strip().split()
    qi = next(
        (i for i, t in enumerate(tokens) if t.upper() in _QUALIFIER_PREFIX),
        None,
    )
    if qi is None:
        return name.strip()
    prefix = _QUALIFIER_PREFIX[tokens[qi].upper()]
    program = " ".join(tokens[:qi])
    year = " ".join(tokens[qi + 1:])
    spec = ""
    if "-" in program:
        base, _, spec = program.partition("-")
        program = base
    code = f"{prefix}{program} {year}".strip()
    if spec:
        code = f"{code}_{spec}"
    return code


# --- Titles ---------------------------------------------------------------

def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "TH"
    else:
        suffix = {1: "ST", 2: "ND", 3: "RD"}.get(n % 10, "TH")
    return f"{n}{suffix}"


def hall_directory_title(date_obj, period: str) -> str:
    weekday = date_obj.strftime("%A").upper()
    month = date_obj.strftime("%B").upper()
    return f"{weekday}, {_ordinal(date_obj.day)} {month} {period} HALL DIRECTORY"


def visa_title(date_obj, period: str) -> str:
    weekday = date_obj.strftime("%A").upper()
    month = date_obj.strftime("%B").upper()
    return (
        f"{weekday} {_ordinal(date_obj.day)}, {month} {date_obj.year} "
        f"- {period} VISA"
    )


# --- Matric ranges --------------------------------------------------------

def _matric_sort_key(matric: str):
    return (0, int(matric)) if matric.isdigit() else (1, matric)


def format_matric_range(matrics: list[str]) -> str:
    """``["2430113585", ..., "2430113616"]`` -> ``"2430113585 - 3616"``.

    Shows the full start matric and abbreviates the end to the suffix that
    differs from the start (keeping at least the last 4 characters).
    """
    cleaned = [m for m in matrics if m]
    if not cleaned:
        return ""
    ordered = sorted(set(cleaned), key=_matric_sort_key)
    start, end = ordered[0], ordered[-1]
    if start == end:
        return start
    common = 0
    while common < len(start) and common < len(end) and start[common] == end[common]:
        common += 1
    cut = min(common, len(end) - 4) if len(end) > 4 else 0
    return f"{start} - {end[cut:]}"


# --- Data builders --------------------------------------------------------

def hall_summary_rows(date_obj, period: str) -> list[dict]:
    """One row per (hall, class) for a slot, from generated seat allocation."""
    qs = (
        SeatArrangement.objects.filter(
            date=date_obj, period=period, seat_number__isnull=False
        )
        .select_related("student", "hall", "cls", "cls__department")
    )
    groups: dict[tuple, dict] = {}
    for sa in qs:
        key = (sa.hall_id, sa.cls_id)
        group = groups.setdefault(
            key, {"hall": sa.hall, "cls": sa.cls, "matrics": []}
        )
        if sa.student and sa.student.matric_no:
            group["matrics"].append(sa.student.matric_no)

    rows = []
    for group in groups.values():
        matrics = group["matrics"]
        rows.append(
            {
                "hall": group["hall"].name,
                # Department code + class name (e.g. "AC ND II").
                "class_name": group["cls"].full_label,
                "count": len(matrics),
                "matric_range": format_matric_range(matrics),
            }
        )
    rows.sort(key=lambda r: (r["class_name"], r["hall"]))
    return rows


def visa_groups(date_obj, period: str) -> list[dict]:
    """VISA codes for a slot, grouped by department.

    Returns ``[{department, department_name, codes: [...]}, ...]`` ordered by
    department code. Used by the on-screen preview's grouped table.
    """
    classes = (
        Class.objects.filter(
            timetable_class__date=date_obj, timetable_class__period=period
        )
        .select_related("department")
        .distinct()
    )
    groups: dict[str, dict] = {}
    for cls in classes:
        code = cls.visa_label
        if not code:
            continue
        dept = cls.department
        dept_code = (dept.slug.upper() if dept and dept.slug else "—")
        group = groups.setdefault(
            dept_code,
            {
                "department": dept_code,
                "department_name": dept.name if dept else "",
                "codes": [],
            },
        )
        group["codes"].append(code)

    result = []
    for dept_code in sorted(groups):
        group = groups[dept_code]
        group["codes"].sort()
        result.append(group)
    return result


def visa_codes(date_obj, period: str) -> list[str]:
    """Flat, sorted VISA codes for a slot (one entry per class). For the PDF."""
    return sorted(
        code
        for group in visa_groups(date_obj, period)
        for code in group["codes"]
    )


# --- Scope resolution -----------------------------------------------------

def all_slots() -> list[tuple]:
    """Every (date, period) in the timetable, ordered, AM before PM."""
    pairs = TimeTable.objects.values_list("date", "period").distinct()
    return sorted(
        {(d, p) for d, p in pairs},
        key=lambda dp: (dp[0], 0 if dp[1] == "AM" else 1),
    )


def resolve_slots(scope: str, date_obj, period: str) -> list[tuple]:
    if scope == "slot":
        return [(date_obj, period)]
    slots = all_slots()
    if scope == "week":
        start = date_obj - timedelta(days=date_obj.weekday())  # Monday
        end = start + timedelta(days=5)  # Saturday
        return [(d, p) for (d, p) in slots if start <= d <= end]
    return slots  # duration


def build_payload(doc: str, scope: str, date_obj, period: str) -> list[dict]:
    """Structured per-slot data shared by the JSON preview and the PDF."""
    out = []
    for d, p in resolve_slots(scope, date_obj, period):
        if doc == "hall":
            out.append(
                {
                    "date": d.isoformat(),
                    "period": p,
                    "title": hall_directory_title(d, p),
                    "rows": hall_summary_rows(d, p),
                }
            )
        else:
            groups = visa_groups(d, p)
            out.append(
                {
                    "date": d.isoformat(),
                    "period": p,
                    "title": visa_title(d, p),
                    # Flat list drives the PDF; grouped list drives the preview.
                    "codes": sorted(
                        code for g in groups for code in g["codes"]
                    ),
                    "groups": groups,
                }
            )
    return out
