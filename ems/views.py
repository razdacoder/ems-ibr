from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.db.models import Q
import pandas as pd
from django.core.paginator import Paginator
from django.contrib import messages
from .forms import LoginForm
from .models import Department, Hall, Course, Class, User


# Create your views here.


def admin_required(view_func):
    decorated_view_func = user_passes_test(lambda user: user.is_staff)(view_func)
    return decorated_view_func


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


@login_required(login_url="login")
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required(login_url="login")
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


@login_required(login_url="login")
def departments(request):
    departments_list = Department.objects.all().order_by("id")
    query = request.GET.get("query")
    if query:
        departments_list = departments_list.filter(
            Q(name__icontains=query) | Q(slug__icontains=query)
        )

    paginator = Paginator(departments_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {"departments": page_obj}
    if request.htmx:
        template_name = "dashboard/pages/departments.html"
    else:
        template_name = "dashboard/departments.html"

    return render(request, template_name=template_name, context=context)


@login_required(login_url="login")
def get_department(request, slug):
    department = get_object_or_404(Department, slug=slug)
    classes = Class.objects.filter(department=department)
    context = {"department": department, "classes": classes}
    if request.htmx:
        template_name = "dashboard/pages/single-department.html"
    else:
        template_name = "dashboard/single-department.html"

    return render(request, template_name=template_name, context=context)


@login_required(login_url="login")
def get_class_course(request, slug, id):
    cls = get_object_or_404(Class, department__slug=slug, id=id)
    context = {"class": cls, "courses": cls.courses.all()}
    if request.htmx:
        template_name = "dashboard/pages/class.html"
    else:
        template_name = "dashboard/class.html"

    return render(request, template_name=template_name, context=context)


@login_required(login_url="login")
@admin_required
def upload_classes(request, dept_slug):
    if request.method == "POST":
        department = get_object_or_404(Department, slug=dept_slug)
        data = request.FILES.get("file")
        dept = pd.read_csv(data)
        dept = dept.to_dict()
        for key in dept["Name"]:
            cls, created = Class.objects.get_or_create(
                name=dept["Name"][key],
                defaults={"size": dept["Size"][key], "department": department},
            )
            if created:
                cls.save()
        return redirect("get_department", department.slug)


@login_required(login_url="login")
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


@login_required(login_url="login")
@admin_required
def halls(request):
    halls_list = Hall.objects.all()
    paginator = Paginator(halls_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {"halls": page_obj}
    if request.htmx:
        template_name = "dashboard/pages/halls.html"
    else:
        template_name = "dashboard/halls.html"

    return render(request, template_name=template_name, context=context)


@login_required(login_url="login")
def timetable(request):
    if request.htmx:
        template_name = "dashboard/pages/timetable.html"
    else:
        template_name = "dashboard/timetable.html"

    return render(request, template_name=template_name)


@login_required(login_url="login")
@admin_required
def distribution(request):
    if request.htmx:
        template_name = "dashboard/pages/distribution.html"
    else:
        template_name = "dashboard/distribution.html"

    return render(request, template_name=template_name)


@login_required(login_url="login")
@admin_required
def allocation(request):
    if request.htmx:
        template_name = "dashboard/pages/allocation.html"
    else:
        template_name = "dashboard/allocation.html"

    return render(request, template_name=template_name)


@login_required(login_url="login")
@admin_required
def manage_users(request):
    users = User.objects.all()
    department_list = Department.objects.all()
    query = request.GET.get("query")
    if query:
        users = users.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query)
        )

    paginator = Paginator(users, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {"users": page_obj, "departments": department_list}

    if request.htmx:
        template_name = "dashboard/pages/manage-users.html"
    else:
        template_name = "dashboard/manage-users.html"

    return render(request, template_name=template_name, context=context)


@require_POST
@login_required(login_url="login")
@admin_required
def add_user(request):
    first_name = request.POST.get("first_name")
    last_name = request.POST.get("last_name")
    email = request.POST.get("email")
    department_slug = request.POST.get("department")
    password = request.POST.get("password")
    password_confirm = request.POST.get("password-confirm")

    if password != password_confirm:
        return render(
            request,
            template_name="dashboard/partials/alert-error.html",
            context={"message": "Passwords do not match"},
        )
    if not Department.objects.filter(slug=department_slug).exists():
        return render(
            request,
            template_name="dashboard/partials/alert-error.html",
            context={
                "message": f"Department with code {department_slug} does not exists"
            },
        )
    if User.objects.filter(email=email).exists():
        return render(
            request,
            template_name="dashboard/partials/alert-error.html",
            context={"message": "Email already exists"},
        )

    user = User.objects.create_user(
        first_name=first_name,
        last_name=last_name,
        email=email,
        department=get_object_or_404(Department, slug=department_slug),
        password=password,
    )
    user.save()
    return render(
        request,
        template_name="dashboard/partials/alert-success.html",
        context={"message": "User created successfully"},
    )


@require_POST
@login_required(login_url="login")
@admin_required
def upload_class_courses(request, id):
    cls = get_object_or_404(Class, id=id)
    data = request.FILES.get("file")
    courses = pd.read_csv(data).to_dict()
    for key in courses["COURSE CODE"]:
        course, created = Course.objects.get_or_create(
            code=courses["COURSE CODE"][key],
            defaults={
                "name": courses["COURSE TITLE"][key],
                "exam_type": courses["EXAM TYPE"][key],
            },
        )
        if created:
            course.save()
        cls.courses.add(course)
        cls.save()
    return render(
        request,
        template_name="dashboard/partials/alert-success.html",
        context={"message": "Courses uploaded successfully"},
    )


@require_POST
@login_required(login_url="login")
@admin_required
def upload_halls(request):
    data = request.FILES.get("file")
    halls = pd.read_csv(data).to_dict()
    for key in halls["EXAM VENUE"]:
        hall, created = Hall.objects.get_or_create(
            name=halls["EXAM VENUE"][key],
            defaults={
                "capacity": halls["CAPACITY"][key],
                "max_students": halls["MAX STUDENTS"][key],
                "min_courses": halls["MIN COURSES"][key],
                "class_x": halls["X AXIS"][key],
                "class_y": halls["Y AXIS"][key],
            },
        )
        if created:
            hall.save()
    return render(
        request,
        template_name="dashboard/partials/alert-success.html",
        context={"message": "Halls uploaded successfully"},
    )
