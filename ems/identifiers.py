"""Cleaning for identifiers typed into spreadsheets (matric and phone numbers).

Excel stores a column of digits as numbers, so a CSV it saves can hold
``2530710047.0`` for the matric number ``2530710047``. Every student upload
path and ``Student.save`` pass values through :func:`clean_number_text` so the
float tail never reaches the database.
"""

import re

_FLOAT_TAIL = re.compile(r"^(\d+)\.0+$")


def clean_number_text(value) -> str:
    """``value`` as trimmed text, with a spreadsheet float tail removed.

    Only an all digit value followed by ``.0``, ``.00``… is changed, so
    matric numbers such as ``ND/2023/001`` or ``20.5`` pass through as typed.
    """
    text = "" if value is None else str(value).strip()
    match = _FLOAT_TAIL.match(text)
    return match.group(1) if match else text
