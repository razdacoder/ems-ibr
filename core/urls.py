from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as serve_media

# API-only: the site and dashboard are a separate TanStack Start service
# (frontend/) that calls this one from the browser, cross-origin.

# Serve uploaded media (e.g. the institution logo). Served regardless of
# DEBUG so the logo also works in production (offload to nginx/WhiteNoise
# later if desired).
_media_prefix = settings.MEDIA_URL.lstrip("/")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("ems.api.urls")),
    re_path(
        rf"^{_media_prefix}(?P<path>.*)$",
        serve_media,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
