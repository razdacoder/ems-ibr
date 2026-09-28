from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from ems.models import BackgroundJob, Class, Student


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.get_or_create(user=instance)


@receiver(post_save, sender=BackgroundJob)
def push_job_progress(sender, instance: BackgroundJob, **kwargs):
    """Broadcast every BackgroundJob change to its WebSocket group."""
    layer = get_channel_layer()
    if layer is None:
        return
    payload = {
        "job_id": instance.job_id,
        "job_type": instance.job_type,
        "status": instance.status,
        "progress": instance.progress_percentage,
        "error_message": instance.error_message,
        "result": instance.result_data if instance.status == "success" else None,
    }
    try:
        async_to_sync(layer.group_send)(
            f"job_{instance.job_id}",
            {"type": "job.progress", "data": payload},
        )
    except Exception:
        # Channel layer may be unavailable in tests or when Redis is down.
        # Don't crash the task — the REST fallback still works.
        pass


# ``Class.size`` is a display copy of the student count. The API write paths
# sync it explicitly (bulk writes skip signals); these receivers cover single
# row writes from anywhere else, such as the Django admin.


@receiver(pre_save, sender=Student)
def remember_student_class(sender, instance: Student, raw=False, **kwargs):
    if raw or instance.pk is None:
        instance._previous_level_id = None
        return
    instance._previous_level_id = (
        Student.objects.filter(pk=instance.pk)
        .values_list("level_id", flat=True)
        .first()
    )


@receiver(post_save, sender=Student)
def sync_class_size_on_save(sender, instance: Student, raw=False, **kwargs):
    if raw:
        return
    Class.objects.sync_student_counts(
        [instance.level_id, getattr(instance, "_previous_level_id", None)]
    )


@receiver(post_delete, sender=Student)
def sync_class_size_on_delete(sender, instance: Student, origin=None, **kwargs):
    # A cascade from deleting the class or department leaves nothing to sync.
    if origin is not None and not (
        isinstance(origin, Student) or getattr(origin, "model", None) is Student
    ):
        return
    Class.objects.sync_student_counts([instance.level_id])
