"""What makes two occurrences the same bug (spec 0004, Fingerprints).

The school is never part of the hash. It is part of the group's unique key,
which keeps the same bug in two schools in two groups (AC-11).
"""
import hashlib
import re

PROJECT_ROOTS = ("ems/", "tenancy/", "core/")
FRAMES_USED = 3

_DIGITS = re.compile(r"\d+")
_QUOTED = re.compile(r"""(["'`]).*?\1""")
# A bundler's content hash before the extension: index-3f9a1c2b.js
_HASHED_FILE = re.compile(r"[-.][0-9a-zA-Z_]{6,}(?=\.\w+$)")


def _hash(*parts):
    return hashlib.sha256("\x1f".join(str(p) for p in parts).encode()).hexdigest()


def class_path(exc_or_type):
    cls = exc_or_type if isinstance(exc_or_type, type) else type(exc_or_type)
    return f"{cls.__module__}.{cls.__qualname__}"


def _module(file):
    path = file[:-3] if file.endswith(".py") else file
    return path.replace("/", ".")


def project_frames(stack):
    """Stored frames that are Ordo's own code (paths are project relative)."""
    return [f for f in stack if f["file"].startswith(PROJECT_ROOTS)]


def for_exception(exc_type, stack):
    """Class path plus ``module:function`` of the innermost project frames,
    or of the innermost frames overall if none are Ordo's."""
    chosen = project_frames(stack) or stack
    where = [f"{_module(f['file'])}:{f['function']}" for f in chosen[-FRAMES_USED:]]
    return _hash("exc", exc_type, *where)


def for_log(logger_name, msg_format):
    """``record.msg`` is the format string before arguments, so no data."""
    return _hash("log", logger_name, msg_format)


def for_job(job_type, exc_type):
    """Expected job failures, and stackless ones, group by job and cause."""
    return _hash("job", job_type, exc_type)


def js_file(url):
    """A script URL's file name without query or bundler hash."""
    name = (url or "").split("?")[0].split("#")[0].rsplit("/", 1)[-1]
    return _HASHED_FILE.sub("", name)


def for_js(name, message, first_file, first_function):
    message = _DIGITS.sub("", _QUOTED.sub("", message or ""))
    return _hash("js", name, message, js_file(first_file), first_function or "")
