from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from ems.models import BackgroundJob


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
