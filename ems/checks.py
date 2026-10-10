"""Deploy checks, run by ``manage.py check --deploy`` before the web service starts."""

from django.conf import settings
from django.core.checks import Error, register


@register(deploy=True)
def check_media_storage(app_configs, **kwargs):
    """Uploaded media must outlive the container in production.

    Without ``CLOUDINARY_URL`` the institution logo is saved to the
    container's own disk: a redeploy wipes it, and with more than one web
    instance only the instance that took the upload has it. Attendance
    sheets then print a placeholder instead of the logo, without an error.
    ``LOCAL_MEDIA_PERSISTENT`` opts out for a single instance with
    ``MEDIA_ROOT`` on a mounted volume.
    """
    if settings.DEBUG:
        return []
    if getattr(settings, "CLOUDINARY_URL", "") or getattr(
        settings, "LOCAL_MEDIA_PERSISTENT", False
    ):
        return []
    return [
        Error(
            "Uploaded media would be saved on the container's own disk.",
            hint=(
                "Set CLOUDINARY_URL so the institution logo survives redeploys "
                "and is shared by every web instance. Set "
                "LOCAL_MEDIA_PERSISTENT=True only for a single instance whose "
                f"MEDIA_ROOT ({settings.MEDIA_ROOT}) is on a persistent volume."
            ),
            id="ems.E001",
        )
    ]
