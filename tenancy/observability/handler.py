"""``ObservabilityLogHandler``: ERROR records on Ordo's own loggers (AC-4).

Attached to ``ems``, ``tenancy`` and ``core`` only, never ``django.request``
(the request receiver covers those) or ``ordo.observability``.
"""
import logging


class ObservabilityLogHandler(logging.Handler):
    def emit(self, record):
        if record.name == "ordo.observability" or record.name.startswith("ordo.observability."):
            return
        try:
            # Imported late: logging is configured before Django apps load.
            from tenancy.observability import capture

            exc = record.exc_info[1] if record.exc_info else None
            if exc is not None:
                capture.capture_exception(exc, "log", culprit=record.name)
            else:
                capture.capture_message(record.name, str(record.msg), record.getMessage())
        except Exception:
            logging.getLogger("ordo.observability").exception("Capturing a log record failed")
