from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

# All non-API, non-admin requests fall through to the React SPA's index.html.
# React Router takes over client-side routing from there.
spa_view = TemplateView.as_view(template_name="index.html")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("ems.api.urls")),
    re_path(r"^.*$", spa_view, name="spa"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
