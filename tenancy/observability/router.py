"""Keeps migrations off the ``observability`` alias. It is the same database
as ``default``; capture code picks it explicitly with ``.using()``."""

ALIAS = "observability"


class ObservabilityRouter:
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == ALIAS:
            return False
        return None
