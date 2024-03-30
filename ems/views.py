from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import pandas as pd
from django.core.paginator import Paginator
from django.contrib import messages
from .forms import LoginForm
from .models import Department, Hall, Course, Class


# Create your views here.


def index(request):
    return render(request, template_name="site/index.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        messages.error(request, "Invalid email or password.")
        return redirect("login")

    return render(
        request,
        template_name="site/login.html",
    )


@login_required(redirect_field_name="login")
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required(redirect_field_name="login")
def dashboard(request):
    departments = Department.objects.all().count()
    halls = Hall.objects.all().count()
    courses = Course.objects.all().count()

    context = {
        "departments_count": departments,
        "halls_count": halls,
        "courses_count": courses,
    }
    if request.htmx:
        template_name = "dashboard/pages/dashboard.html"
    else:
        template_name = "dashboard/index.html"

    return render(request, template_name=template_name, context=context)


@login_required(redirect_field_name="login")
def departments(request):
    departmets_list = Department.objects.all().order_by("id")
    query = request.GET.get("query")
    if query:
        departmets_list = departmets_list.filter(
            Q(name__icontains=query) | Q(slug__icontains=query)
        )

    paginator = Paginator(departmets_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {"departments": page_obj}
    if request.htmx:
        template_name = "dashboard/pages/departments.html"
    else:
        template_name = "dashboard/departments.html"

    return render(request, template_name=template_name, context=context)


@login_required(redirect_field_name="login")
def get_depertment(request, slug):
    department = get_object_or_404(Department, slug=slug)
    clases = Class.objects.filter(department=department)
    context = {"department": department, "clases": clases}
    if request.htmx:
        template_name = "dashboard/pages/single-department.html"
    else:
        template_name = "dashboard/single-department.html"

    return render(request, template_name=template_name, context=context)


@login_required(redirect_field_name="login")
def upload_departments(request):
    if request.method == "POST":
        data = request.FILES.get("file")
        dept = pd.read_csv(data)
        dept = dept.to_dict()
        for key in dept["Code"]:
            department, created = Department.objects.get_or_create(
                slug=dept["Code"][key],
                defaults={"name": dept["Name"][key]},
            )
            if created:
                department.save()
        return redirect("department")


@login_required(redirect_field_name="login")
def halls(request):
    if request.htmx:
        template_name = "dashboard/pages/halls.html"
    else:
        template_name = "dashboard/halls.html"

    return render(request, template_name=template_name)


@login_required(redirect_field_name="login")
def timetable(request):
    if request.htmx:
        template_name = "dashboard/pages/timetable.html"
    else:
        template_name = "dashboard/timetable.html"

    return render(request, template_name=template_name)


@login_required(redirect_field_name="login")
def distribution(request):
    if request.htmx:
        template_name = "dashboard/pages/distribution.html"
    else:
        template_name = "dashboard/distribution.html"

    return render(request, template_name=template_name)


@login_required(redirect_field_name="login")
def allocation(request):
    if request.htmx:
        template_name = "dashboard/pages/allocation.html"
    else:
        template_name = "dashboard/allocation.html"

    return render(request, template_name=template_name)


@login_required(redirect_field_name="login")
def manage_users(request):
    if request.htmx:
        template_name = "dashboard/pages/manage-users.html"
    else:
        template_name = "dashboard/manage-users.html"

    return render(request, template_name=template_name)
