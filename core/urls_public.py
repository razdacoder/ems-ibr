from django.urls import include, path

# The public schema: admin.<base> (platform console API) and api.<base>
# (the marketing site's server side calls). No school data and no media here.

urlpatterns = [
    path("api/public/", include("ems.api.public_urls")),
]
