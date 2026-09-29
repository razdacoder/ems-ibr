"""Hall groups, the order halls are used in, and course limits per hall.

* **Group**: halls that stand together (AUD, BE, BJ ...). Filled from the
  hall's name unless set by hand. ``GenerationConstraints.hall_group_order``
  lists groups so that neighbours in the list are neighbours on the ground.
* **Walk order**: distribution fills halls one at a time in this order and
  allocation seats them in it: group by group in the configured order,
  biggest hall first inside a group. Groups not in the order come after,
  the group with the biggest hall first. A course that runs out of room in
  one hall carries on into the next hall of the walk, so its halls stay
  together and spill only into the neighbouring group.
* **Course limit**: most different courses one hall may hold, from the
  size tiers in ``GenerationConstraints.hall_course_limits``.

Everything here is pure.
"""

import re

DEFAULT_COURSE_LIMITS = [
    {"max_seats": 120, "courses": 4},
    {"max_seats": 300, "courses": 6},
    {"max_seats": None, "courses": 8},
]


def group_from_name(name: str) -> str:
    """The letters a hall's name starts with: "BE 3" -> "BE", "BJ4" -> "BJ",
    "AUD 1" -> "AUD". A name with no leading letters is its own group."""
    name = (name or "").strip()
    match = re.match(r"[A-Za-z]+", name)
    return (match.group(0) if match else name).upper()


def normalise_group_order(order) -> list:
    """Group names, upper case, blanks and repeats dropped."""
    seen, out = set(), []
    for group in order or ():
        group = str(group).strip().upper()
        if group and group not in seen:
            seen.add(group)
            out.append(group)
    return out


def normalise_course_limits(tiers) -> list:
    """Tiers sorted by ``max_seats`` with the open tier (``None``) last.
    Raises ``ValueError`` with a message fit for the user."""
    if not isinstance(tiers, list) or not tiers:
        raise ValueError("Give at least one size tier.")
    cleaned = []
    for tier in tiers:
        try:
            max_seats = tier.get("max_seats")
            max_seats = None if max_seats in (None, "") else int(max_seats)
            courses = int(tier.get("courses"))
        except (AttributeError, TypeError, ValueError):
            raise ValueError("Each tier needs a seat limit (or none) and a course count.")
        if courses < 1:
            raise ValueError("A hall must be allowed at least one course.")
        if max_seats is not None and max_seats < 1:
            raise ValueError("Seat limits must be positive.")
        cleaned.append({"max_seats": max_seats, "courses": courses})
    open_tiers = [t for t in cleaned if t["max_seats"] is None]
    if len(open_tiers) != 1:
        raise ValueError("Exactly one tier must have no seat limit (the biggest halls).")
    bounded = sorted((t for t in cleaned if t["max_seats"] is not None),
                     key=lambda t: t["max_seats"])
    if len({t["max_seats"] for t in bounded}) != len(bounded):
        raise ValueError("Two tiers have the same seat limit.")
    return bounded + open_tiers


def course_limit(seats: int, tiers) -> int:
    """Most courses a hall of ``seats`` may hold under ``tiers``."""
    for tier in normalise_course_limits(tiers or DEFAULT_COURSE_LIMITS):
        if tier["max_seats"] is None or seats <= tier["max_seats"]:
            return tier["courses"]
    return DEFAULT_COURSE_LIMITS[-1]["courses"]  # unreachable: one tier is open


def group_ranks(halls, group_order) -> dict:
    """``{group: rank}`` for ``halls``, an iterable of ``(group, seats)``.
    Configured groups keep their order; the rest follow, the group with the
    biggest hall first, then by name."""
    order = normalise_group_order(group_order)
    biggest: dict[str, int] = {}
    for group, seats in halls:
        biggest[group] = max(biggest.get(group, 0), seats)
    ranks = {group: i for i, group in enumerate(order)}
    rest = sorted(
        (g for g in biggest if g not in ranks), key=lambda g: (-biggest[g], g)
    )
    for group in rest:
        ranks[group] = len(ranks)
    return ranks


def walk_key(ranks: dict, group: str, seats: int, name: str) -> tuple:
    """Sort key of one hall in the walk order."""
    return (ranks.get(group, len(ranks)), -seats, name)
