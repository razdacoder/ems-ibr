from django.shortcuts import render

# Create your views here.


def index(request):
    return render(request, template_name="site/index.html")


def login_view(request):
    return render(request, template_name="site/login.html")


def dashboard(request):
    return render(request, template_name="dashboard/index.html")
