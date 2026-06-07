from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.static import serve as serve_media

# All non-API, non-admin requests fall through to the React SPA's index.html.
# React Router takes over client-side routing from there.
spa_view = TemplateView.as_view(template_name="index.html")

# Serve uploaded media (e.g. the institution logo). This MUST come before the
# SPA catch-all below — otherwise ``^.*$`` swallows ``/media/...`` and returns
# index.html, which breaks image requests. Served regardless of DEBUG so the
# logo also works in production (offload to nginx/WhiteNoise later if desired).
_media_prefix = settings.MEDIA_URL.lstrip("/")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("ems.api.urls")),
    re_path(
        rf"^{_media_prefix}(?P<path>.*)$",
        serve_media,
        {"document_root": settings.MEDIA_ROOT},
    ),
    re_path(r"^.*$", spa_view, name="spa"),
]
