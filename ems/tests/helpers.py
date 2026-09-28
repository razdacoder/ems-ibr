"""Small builders shared by the test modules."""
import contextlib
import io
from itertools import count

from ems.models import Class, Course, Department, Faculty, Hall, Student, TimeTable

_seq = count(1)


def make_department(slug=None):
    n = next(_seq)
    faculty = Faculty.objects.create(name=f"Faculty {n}", slug=f"fac{n}")
    slug = slug or f"d{n}"
    return Department.objects.create(name=f"Department {slug}", slug=slug, faculty=faculty)


def make_class(size, department=None, name="ND I"):
    return Class.objects.create(
        name=name, size=size, department=department or make_department()
    )


def listed_class(students, department=None, name="ND I"):
    """A class with ``students`` real students uploaded. Planning counts the
    uploaded list, never ``Class.size`` (spec 0001)."""
    cls = make_class(students, department, name)
    tag = next(_seq)
    Student.objects.bulk_create(
        Student(
            first_name="Ada", last_name=f"L{tag}-{n}", matric_no=f"L{tag:05}{n:05}",
            email=f"l{tag}-{n}@example.com", department=cls.department, level=cls,
        )
        for n in range(students)
    )
    return cls


def make_course(code):
    return Course.objects.create(name=f"Course {code}", code=code, exam_type="PBE")


def make_hall(name, rows, cols):
    return Hall.objects.create(
        name=name, capacity=rows * cols, max_students=0, min_courses=0,
        rows=rows, columns=cols,
    )


def schedule(cls, course, date="2026-08-17", period="AM"):
    return TimeTable.objects.create(class_obj=cls, course=course, date=date, period=period)


def enrol(cls, matrics):
    return [
        Student.objects.create(
            first_name="Ada", last_name=m, matric_no=m, email=f"{m}@example.com",
            department=cls.department, level=cls,
        )
        for m in matrics
    ]


def quietly(fn, *args, **kwargs):
    """Call ``fn`` with its debug prints swallowed."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)
