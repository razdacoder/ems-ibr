"""``/api/platform/``: public urlconf only, never on a school host."""
from django.urls import path

from tenancy import views

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
]
