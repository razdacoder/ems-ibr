from django.urls import re_path

from ems.api.consumers import JobProgressConsumer

websocket_urlpatterns = [
    re_path(r"^ws/jobs/(?P<job_id>[\w-]+)/$", JobProgressConsumer.as_asgi()),
]
