from django.urls import path
from . import views

urlpatterns = [
    path("", view=views.index, name="home"),
    path("login/", view=views.login_view, name="login"),
    path("dashboard/", view=views.dashboard, name="dashboard"),
]
