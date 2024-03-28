from django.shortcuts import render

# Create your views here.


def index(request):
    return render(request, template_name="site/index.html")


def login_view(request):
    return render(request, template_name="site/login.html")


def dashboard(request):
    if request.htmx:
        template_name = "dashboard/pages/dashboard.html"
    else:
        template_name = "dashboard/index.html"

    return render(request, template_name=template_name)


def departments(request):
    if request.htmx:
        template_name = "dashboard/pages/departments.html"
    else:
        template_name = "dashboard/departments.html"

    return render(request, template_name=template_name)
