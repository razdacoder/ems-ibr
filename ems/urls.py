from django.urls import path
from . import views

urlpatterns = [
    path("", view=views.index, name="home"),
    path("login/", view=views.login_view, name="login"),
    path("logout/", view=views.logout_view, name="logout"),
    path("dashboard/", view=views.dashboard, name="dashboard"),
    path("departments/", view=views.departments, name="department"),
    path("halls/", view=views.halls, name="halls"),
    path("timetable/", view=views.timetable, name="timetable"),
    path("distribution/", view=views.distribution, name="distribution"),
    path("allocation/", view=views.allocation, name="allocation"),
    path("manage-users/", view=views.manage_users, name="manage_users"),
]
