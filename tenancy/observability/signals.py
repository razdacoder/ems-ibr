"""Celery task failures (AC-2) and the ``BackgroundJob`` safety net (AC-3)."""
from celery.signals import task_failure
from django.db.models.signals import post_init, post_save

from tenancy.observability import capture


@task_failure.connect(dispatch_uid="ordo_observability_task_failure")
def task_failed(sender=None, exception=None, **kwargs):
    # Runs before the library's postrun handler restores the schema, so the
    # task's school is still the connection's tenant.
    try:
        name = getattr(sender, "name", "") or ""
        capture.capture_exception(exception, "task", culprit=name, task_name=name)
    except Exception:
        capture.logger.exception("Capturing a task failure failed")


def job_loaded(sender, instance, **kwargs):
    instance._ordo_loaded_status = instance.__dict__.get("status")


def job_saved(sender, instance, created=False, **kwargs):
    """A job that became ``failed`` without a failure site reporting it:
    record it without a stack, so a new failure site can't go unseen."""
    try:
        became_failed = instance.status == "failed" and (
            created or getattr(instance, "_ordo_loaded_status", None) != "failed"
        )
        if became_failed and not getattr(instance, "_ordo_observed", False):
            capture.job_failed(instance)
        instance._ordo_loaded_status = instance.status
    except Exception:
        capture.logger.exception("Checking a saved job failed")


def connect():
    from ems.models import BackgroundJob

    post_init.connect(job_loaded, sender=BackgroundJob, dispatch_uid="ordo_observability_job_loaded")
    post_save.connect(job_saved, sender=BackgroundJob, dispatch_uid="ordo_observability_job_saved")
