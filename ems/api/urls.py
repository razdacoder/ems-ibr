from django.urls import include, path

from ems.api.routers import router
from ems.api.views.auth import LoginView, LogoutView, MeView
from ems.api.views.system import (
    DashboardStatsView,
    EnableBulkUploadView,
    ResetSystemView,
    SystemSettingsView,
)
from ems.api.views.uploads import (
    BulkUploadView,
    ClassCoursesUploadView,
    ClassStudentsUploadView,
    ClassesForDepartmentUploadView,
    CourseUploadView,
    DepartmentUploadView,
    HallUploadView,
)
from ems.api.views.jobs import (
    GenerateAllocationView,
    GenerateDistributionView,
    GenerateTimetableView,
    ManualSeatAssignmentView,
)
from ems.api.views.scheduling import (
    AllocationListView,
    DistributionListView,
    DistributionStatisticsView,
    HallAllocationView,
    TimetableDatesView,
    TimetableListView,
)
from ems.api.views.exports import (
    ArrangementExportView,
    AttendanceSheetsView,
    BroadsheetView,
    DistributionExportView,
    TimetableExportView,
)
from ems.api.views.public import FeatureDetailView, FeaturesIndexView

auth_patterns = [
    path("login/", LoginView.as_view(), name="api-login"),
    path("logout/", LogoutView.as_view(), name="api-logout"),
    path("me/", MeView.as_view(), name="api-me"),
]

system_patterns = [
    path("settings/", SystemSettingsView.as_view(), name="api-settings"),
    path("dashboard/", DashboardStatsView.as_view(), name="api-dashboard"),
    path("reset/", ResetSystemView.as_view(), name="api-reset"),
    path(
        "enable-bulk-upload/",
        EnableBulkUploadView.as_view(),
        name="api-enable-bulk-upload",
    ),
]


upload_patterns = [
    path("departments/", DepartmentUploadView.as_view(), name="api-upload-departments"),
    path("halls/", HallUploadView.as_view(), name="api-upload-halls"),
    path("courses/", CourseUploadView.as_view(), name="api-upload-courses"),
    path(
        "classes/<slug:dept_slug>/",
        ClassesForDepartmentUploadView.as_view(),
        name="api-upload-classes",
    ),
    path(
        "class-courses/<int:class_id>/",
        ClassCoursesUploadView.as_view(),
        name="api-upload-class-courses",
    ),
    path(
        "class-students/<int:class_id>/",
        ClassStudentsUploadView.as_view(),
        name="api-upload-class-students",
    ),
    path("bulk/", BulkUploadView.as_view(), name="api-upload-bulk"),
]


scheduling_patterns = [
    path("timetable/", TimetableListView.as_view(), name="api-timetable"),
    path(
        "timetable/dates/",
        TimetableDatesView.as_view(),
        name="api-timetable-dates",
    ),
    path(
        "timetable/generate/",
        GenerateTimetableView.as_view(),
        name="api-generate-timetable",
    ),
    path("distribution/", DistributionListView.as_view(), name="api-distribution"),
    path(
        "distribution/statistics/",
        DistributionStatisticsView.as_view(),
        name="api-distribution-statistics",
    ),
    path(
        "distribution/generate/",
        GenerateDistributionView.as_view(),
        name="api-generate-distribution",
    ),
    path("allocation/", AllocationListView.as_view(), name="api-allocation"),
    path(
        "allocation/hall/",
        HallAllocationView.as_view(),
        name="api-allocation-hall",
    ),
    path(
        "allocation/generate/",
        GenerateAllocationView.as_view(),
        name="api-generate-allocation",
    ),
    path(
        "allocation/manual-assign/",
        ManualSeatAssignmentView.as_view(),
        name="api-allocation-manual-assign",
    ),
]


export_patterns = [
    path("timetable/", TimetableExportView.as_view(), name="api-export-timetable"),
    path(
        "distribution/",
        DistributionExportView.as_view(),
        name="api-export-distribution",
    ),
    path(
        "arrangement/",
        ArrangementExportView.as_view(),
        name="api-export-arrangement",
    ),
    path(
        "attendance-sheets/",
        AttendanceSheetsView.as_view(),
        name="api-export-attendance-sheets",
    ),
    path("broadsheet/", BroadsheetView.as_view(), name="api-export-broadsheet"),
]

public_patterns = [
    path("features/", FeaturesIndexView.as_view(), name="api-public-features"),
    path(
        "features/<slug:slug>/",
        FeatureDetailView.as_view(),
        name="api-public-feature-detail",
    ),
]


urlpatterns = [
    path("auth/", include(auth_patterns)),
    path("system/", include(system_patterns)),
    path("uploads/", include(upload_patterns)),
    path("exports/", include(export_patterns)),
    path("public/", include(public_patterns)),
    path("", include(scheduling_patterns)),
    path("", include(router.urls)),
]
