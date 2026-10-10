from django.urls import path

from ems.api.views.public import FeatureDetailView, FeaturesIndexView

# No school data: served on api.<base> for the marketing site, from the
# public schema (core.urls_public).
urlpatterns = [
    path("features/", FeaturesIndexView.as_view(), name="api-public-features"),
    path(
        "features/<slug:slug>/",
        FeatureDetailView.as_view(),
        name="api-public-feature-detail",
    ),
]
