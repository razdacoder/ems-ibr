from django.urls import re_path

from ems.api.consumers import JobProgressConsumer, NotificationConsumer

websocket_urlpatterns = [
    re_path(r"^ws/jobs/(?P<job_id>[\w-]+)/$", JobProgressConsumer.as_asgi()),
    re_path(r"^ws/notifications/$", NotificationConsumer.as_asgi()),
]
