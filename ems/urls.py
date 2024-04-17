from django.urls import path
from . import views

urlpatterns = [
    path("", view=views.index, name="home"),
    path("login/", view=views.login_view, name="login"),
    path("logout/", view=views.logout_view, name="logout"),
    path("dashboard/", view=views.dashboard, name="dashboard"),
    path("departments/", view=views.departments, name="department"),
    path(
        "upload-departments/", view=views.upload_departments, name="upload-departments"
    ),
    path("halls/", view=views.halls, name="halls"),
    path("timetable/", view=views.timetable, name="timetable"),
    path("distribution/", view=views.distribution, name="distribution"),
    path("allocation/", view=views.allocation, name="allocation"),
    path("manage-users/", view=views.manage_users, name="manage_users"),
    path("departments/<str:slug>/", view=views.get_department, name="get_department"),
    path(
        "upload-classes/<str:dept_slug>/",
        view=views.upload_classes,
        name="upload_classes",
    ),
    path(
        "departments/<str:slug>/<int:id>/",
        view=views.get_class_course,
        name="get_class_course",
    ),
    path("add-user/", view=views.add_user, name="add-user"),
]
