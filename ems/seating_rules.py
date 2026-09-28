"""The per course seating rule, in one place (spec 0002).

Timetable, distribution, the allocator, reconcile and manual assignment all
read the limits and the neighbour sets from here, so the distribution model
and the seater cannot drift apart.

* ``strict``: no two students of a course touch in any of the 8 directions.
  One course is confined to one ``(r % 2, c % 2)`` quarter of a hall.
* ``relaxed``: only side, front and back neighbours are blocked. The course
  sits on the even parity seats (``r % 2 == c % 2``, quarters ``(0,0)`` and
  ``(1,1)``), which never share an edge. Used for a paper course too big for
  one period under the strict rule. At most one per period.

Everything here is pure: callers pass hall sizes as ``(rows, cols)`` pairs.
"""

from functools import lru_cache

STRICT = "strict"
RELAXED = "relaxed"
REFUSED = "refused"

RULE_CHOICES = [(STRICT, "Strict"), (RELAXED, "Relaxed")]

# Printed under the course details on every attendance sheet of a relaxed
# course, so invigilators watch the diagonal neighbours.
RELAXED_SHEET_LINE = "SEATING: RELAXED (DIAGONAL NEIGHBOURS ALLOWED)"

_EIGHT = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]
_FOUR = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def neighbours(rule: str) -> list:
    """Offsets a same course student may not occupy under ``rule``."""
    return list(_FOUR if rule == RELAXED else _EIGHT)


def hall_per_course_slice(rows: int, cols: int, pattern: str = "checkerboard") -> int:
    """Largest course that's guaranteed to fit any quarter of the hall.

    Each course is confined to one ``(r%2, c%2)`` parity quarter so all its
    students stay pairwise non-8-dir-adjacent. When ``rows`` or ``cols`` is
    odd the four quarters have unequal sizes (e.g. a 15×20 hall has two
    80-cell and two 70-cell quarters). To guarantee zero adjacency-overflow
    we cap at the *smallest* quarter — ``floor(r/2) × floor(c/2)`` — rather
    than the largest. Pattern is irrelevant; same-course adjacency binds.
    """
    del pattern
    if rows <= 0 or cols <= 0:
        return 0
    return max(1, rows // 2) * max(1, cols // 2)


def largest_quarter(rows: int, cols: int) -> int:
    """Seats in the biggest ``(r%2, c%2)`` quarter, quarter ``(0,0)``.

    Distribution caps a strict course per hall at this, not at
    :func:`hall_per_course_slice`: a course may fill a bigger quarter
    whole. ``_quarters_can_seat`` still verifies every bite, so a course is
    only given the big quarter while one is free. ``strict_limit`` stays on
    the smallest quarter so timetable classification remains a guarantee."""
    if rows <= 0 or cols <= 0:
        return 0
    return ((rows + 1) // 2) * ((cols + 1) // 2)


def even_half(rows: int, cols: int) -> int:
    """Even parity seats of the hall: quarters ``(0,0)`` + ``(1,1)``. The
    most one relaxed course can take in it."""
    if rows <= 0 or cols <= 0:
        return 0
    return ((rows + 1) // 2) * ((cols + 1) // 2) + (rows // 2) * (cols // 2)


def strict_limit(halls) -> int:
    """Students one strict course can be seated for across ``halls`` in one
    period. A hall with fewer than 2 rows or 2 columns counts as 0."""
    return sum(
        hall_per_course_slice(r, c) for r, c in halls if r >= 2 and c >= 2
    )


def relaxed_limit(halls) -> int:
    """Students one relaxed course can be seated for across ``halls``."""
    return sum(even_half(r, c) for r, c in halls)


def classify(students: int, strict_limit: int, relaxed_limit: int) -> str:
    """The rule a paper course of ``students`` gets. CBE is never classified."""
    if students <= strict_limit:
        return STRICT
    if students <= relaxed_limit:
        return RELAXED
    return REFUSED


def even_seats(rows: int, cols: int) -> list:
    """Even parity seats in seat number order (row by row, left to right).
    The allocator seats a relaxed course along exactly this list."""
    return [(r, c) for r in range(rows) for c in range(cols) if r % 2 == c % 2]


@lru_cache(maxsize=4096)
def relaxed_quarter_usage(rows: int, cols: int, k: int) -> tuple:
    """``(in_q00, in_q11)``: how many of the first ``k`` seats of
    :func:`even_seats` fall in quarter ``(0,0)`` and quarter ``(1,1)``.
    Cached: the distribution model asks inside a binary search per hall."""
    in_q00 = sum(1 for r, _c in even_seats(rows, cols)[: max(k, 0)] if r % 2 == 0)
    return in_q00, min(max(k, 0), even_half(rows, cols)) - in_q00
