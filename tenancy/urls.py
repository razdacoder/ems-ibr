"""``/api/platform/``: public urlconf only, never on a school host."""
from django.urls import path

from tenancy import school_views, views

urlpatterns = [
    path("auth/login/", views.LoginView.as_view()),
    path("auth/totp/", views.TotpView.as_view()),
    path("auth/enroll/", views.EnrollView.as_view()),
    path("auth/logout/", views.LogoutView.as_view()),
    path("me/", views.MeView.as_view()),
    path("admins/", views.AdminListView.as_view()),
    path("admins/accept/", views.AcceptInviteView.as_view()),
    path("admins/<int:pk>/", views.AdminDetailView.as_view()),
    path("admins/<int:pk>/reset-2fa/", views.AdminResetTwoFactorView.as_view()),
    path("admins/<int:pk>/unlock/", views.AdminUnlockView.as_view()),
    path("admins/<int:pk>/resend-invite/", views.AdminResendInviteView.as_view()),
    path("audit/", views.AuditLogView.as_view()),
    path("plans/", school_views.PlanListView.as_view()),
    path("plans/<int:pk>/", school_views.PlanDetailView.as_view()),
    path("schools/", school_views.SchoolListView.as_view()),
    path("schools/<int:pk>/", school_views.SchoolDetailView.as_view()),
    path("schools/<int:pk>/retry/", school_views.SchoolRetryView.as_view()),
    path("schools/<int:pk>/resend-invite/", school_views.SchoolResendInviteView.as_view()),
    path("schools/<int:pk>/suspend/", school_views.SchoolSuspendView.as_view()),
    path("schools/<int:pk>/reactivate/", school_views.SchoolReactivateView.as_view()),
    path("schools/<int:pk>/delete/", school_views.SchoolDeleteView.as_view()),
    path("schools/<int:pk>/restore/", school_views.SchoolRestoreView.as_view()),
    path(
        "schools/<int:pk>/support-sessions/",
        school_views.SchoolSupportSessionsView.as_view(),
    ),
    path(
        "support-sessions/<int:pk>/end/",
        school_views.SupportSessionEndView.as_view(),
    ),
]
