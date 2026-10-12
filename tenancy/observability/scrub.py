"""Message scrubbing and stack trimming (AC-8).

A denylist of patterns: anything that looks like personal data or a secret
is masked before a message is stored. It runs on every message and title,
whatever the source. Review it when a new kind of error message shows up.
"""
import re
from pathlib import Path

from django.conf import settings

MESSAGE_MAX = 1000
TITLE_MAX = 255
STACK_MAX = 50
CODE_MAX = 200

# Order matters: whole Postgres DETAIL lines and Key (...)=(...) values go
# first, before the narrower patterns cut them into pieces.
_RULES = (
    (re.compile(r"^(\s*DETAIL:).*$", re.MULTILINE), r"\1 [scrubbed]"),
    (re.compile(r"(Key \([^)]*\))=\(.*?\)(?=\s|$|,|\.)"), r"\1=([scrubbed])"),
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[email]"),
    (re.compile(r'"[^"\n]*"'), '"[value]"'),
    (re.compile(r"'[^'\n]*'"), "'[value]'"),
    # A long run of letters and digits mixed: an API key, a token, a hash.
    (
        re.compile(r"\b(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{20,}\b"),
        "[token]",
    ),
    # Phone numbers: a leading + or 0 and 7 or more digits, maybe spaced.
    (re.compile(r"(?<![\w])\+?\d[\d\s().-]{6,}\d(?![\w])"), "[number]"),
    (re.compile(r"\d{5,}"), "[number]"),
)


def scrub(text, limit=MESSAGE_MAX):
    """``text`` with every rule applied, cut to ``limit`` characters."""
    text = str(text or "")
    for pattern, replacement in _RULES:
        text = pattern.sub(replacement, text)
    return text[:limit]


def title(text):
    return scrub(text, TITLE_MAX).splitlines()[0][:TITLE_MAX] if text else ""


def _relative(filename):
    try:
        return str(Path(filename).resolve().relative_to(settings.BASE_DIR))
    except (ValueError, OSError):
        return filename


def frames(tb_frames):
    """``traceback.FrameSummary`` items as stored: at most 50, innermost
    last, with project relative paths. Code lines are source code, not data,
    but long ones are cut."""
    rows = []
    for frame in list(tb_frames)[-STACK_MAX:]:
        rows.append(
            {
                "file": _relative(frame.filename)[:TITLE_MAX],
                "line": frame.lineno,
                "function": str(frame.name)[:TITLE_MAX],
                "code": (frame.line or "")[:CODE_MAX],
            }
        )
    return rows
