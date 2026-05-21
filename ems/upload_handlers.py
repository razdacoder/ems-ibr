"""Shared CSV/Excel ingestion logic for the upload endpoints.

Each handler accepts a Django UploadedFile (and any resource-specific arg)
and returns a dict ``{"created": int, "updated": int}``. Validation
problems raise ``UploadError`` with a human-readable message — the API
view layer turns those into 400 responses.

The API endpoints are the only callers; the legacy HTML upload views have
been deleted along with the templates.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd
from django.db import transaction

from ems.models import Class, Course, Department, Student


class UploadError(ValueError):
    """Raised for any human-correctable problem with an uploaded file."""


def _read_csv(file) -> pd.DataFrame:
    try:
        return pd.read_csv(file)
    except Exception as exc:  # pragma: no cover - pandas error surface is wide
        raise UploadError(
            f"Could not read file: {exc}. Please confirm it is a valid CSV."
        ) from exc


def _check_columns(df: pd.DataFrame, required: Iterable[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise UploadError(f"Missing required columns: {', '.join(missing)}")


def _check_no_duplicates(df: pd.DataFrame, column: str, label: str) -> None:
    dupes = df[df.duplicated(subset=[column], keep=False)][column].tolist()
    if dupes:
        sample = ", ".join(sorted(set(map(str, dupes)))[:5])
        suffix = "…" if len(set(dupes)) > 5 else ""
        raise UploadError(f"Duplicate {label} found in file: {sample}{suffix}")


def upload_departments(file) -> dict[str, int]:
    df = _read_csv(file)
    _check_columns(df, ["Name", "Code"])
    _check_no_duplicates(df, "Code", "department codes")

    created = updated = 0
    with transaction.atomic():
        for row in df.to_dict("records"):
            slug = str(row["Code"]).strip().upper()
            name = str(row["Name"]).strip()
            obj, was_created = Department.objects.get_or_create(
                slug=slug, defaults={"name": name}
            )
            if was_created:
                created += 1
            else:
                if obj.name != name:
                    obj.name = name
                    obj.save(update_fields=["name"])
                updated += 1
    return {"created": created, "updated": updated}


def upload_halls(file) -> dict[str, int]:
    from ems.models import Hall

    df = _read_csv(file)
    _check_columns(
        df,
        ["EXAM VENUE", "CAPACITY", "MAX STUDENTS", "MIN COURSES", "ROWS", "COLS"],
    )
    _check_no_duplicates(df, "EXAM VENUE", "hall names")

    created = updated = 0
    with transaction.atomic():
        for row in df.to_dict("records"):
            defaults = {
                "capacity": int(row["CAPACITY"]),
                "max_students": int(row["MAX STUDENTS"]),
                "min_courses": int(row["MIN COURSES"]),
                "rows": int(row["ROWS"]),
                "columns": int(row["COLS"]),
            }
            hall, was_created = Hall.objects.get_or_create(
                name=str(row["EXAM VENUE"]).strip(), defaults=defaults
            )
            if was_created:
                created += 1
            else:
                for k, v in defaults.items():
                    setattr(hall, k, v)
                hall.save()
                updated += 1
    return {"created": created, "updated": updated}


def upload_courses(file) -> dict[str, int]:
    df = _read_csv(file)
    _check_columns(df, ["COURSE CODE", "COURSE TITLE", "EXAM TYPE"])
    _check_no_duplicates(df, "COURSE CODE", "course codes")

    created = updated = 0
    with transaction.atomic():
        for row in df.to_dict("records"):
            code = str(row["COURSE CODE"]).strip()
            exam_type = str(row["EXAM TYPE"]).strip().upper()
            if exam_type not in ("PBE", "CBE"):
                raise UploadError(
                    f"Row with code {code} has invalid exam type '{exam_type}'. "
                    "Allowed values are PBE or CBE."
                )
            name = str(row["COURSE TITLE"]).strip()
            course, was_created = Course.objects.get_or_create(
                code=code, defaults={"name": name, "exam_type": exam_type}
            )
            if was_created:
                created += 1
            else:
                course.name = name
                course.exam_type = exam_type
                course.save()
                updated += 1
    return {"created": created, "updated": updated}


def upload_classes_for_department(file, department: Department) -> dict[str, int]:
    df = _read_csv(file)
    _check_columns(df, ["Name", "Size"])
    _check_no_duplicates(df, "Name", "class names")

    created = updated = 0
    with transaction.atomic():
        for row in df.to_dict("records"):
            name = str(row["Name"]).strip()
            size = int(row["Size"]) if pd.notna(row["Size"]) else 0
            cls, was_created = Class.objects.get_or_create(
                name=name,
                department=department,
                defaults={"size": size},
            )
            if was_created:
                created += 1
            elif cls.size != size:
                cls.size = size
                cls.save(update_fields=["size"])
                updated += 1
            else:
                updated += 1
    return {"created": created, "updated": updated}


def upload_class_courses(file, cls: Class) -> dict[str, int]:
    if not Course.objects.exists():
        raise UploadError(
            "No courses found in the system. Upload the institutional course "
            "catalog before assigning courses to a class."
        )
    df = _read_csv(file)
    _check_columns(df, ["COURSE CODE"])

    codes_in_file = [
        str(c).strip()
        for c in df["COURSE CODE"].tolist()
        if pd.notna(c) and str(c).strip() and str(c).strip().lower() != "nan"
    ]
    if not codes_in_file:
        raise UploadError("No course codes found in the uploaded file.")
    existing = set(Course.objects.values_list("code", flat=True))
    invalid = [c for c in codes_in_file if c not in existing]
    if invalid:
        sample = ", ".join(sorted(set(invalid))[:10])
        raise UploadError(
            f"The following course codes do not exist in the system: {sample}"
            + ("…" if len(set(invalid)) > 10 else "")
        )

    courses = Course.objects.filter(code__in=codes_in_file)
    added = 0
    with transaction.atomic():
        for course in courses:
            if not cls.courses.filter(pk=course.pk).exists():
                cls.courses.add(course)
                added += 1
    return {"created": added, "updated": len(codes_in_file) - added}


def upload_class_students(file, cls: Class) -> dict[str, int]:
    df = _read_csv(file)
    _check_columns(
        df,
        ["MATRIC NUMBER", "FIRSTNAME", "LASTNAME", "EMAIL", "PHONE NUMBER"],
    )
    # Drop rows with no matric number (blank trailing rows would otherwise
    # become the literal string "nan" after astype(str) and trigger the
    # duplicate-matric-number check).
    df = df.dropna(subset=["MATRIC NUMBER"])
    df = df.astype(str).apply(lambda c: c.str.strip())
    df = df[~df["MATRIC NUMBER"].str.lower().isin(("", "nan"))]
    if df.empty:
        raise UploadError("No student rows with a matric number were found in the file.")
    _check_no_duplicates(df, "MATRIC NUMBER", "matric numbers")

    matric_numbers = df["MATRIC NUMBER"].tolist()
    existing = {
        s.matric_no: s
        for s in Student.objects.filter(matric_no__in=matric_numbers).only(
            "id",
            "matric_no",
            "first_name",
            "last_name",
            "email",
            "phone",
            "department_id",
            "level_id",
        )
    }

    to_create: list[Student] = []
    to_update: list[Student] = []
    for record in df.to_dict("records"):
        matric = record["MATRIC NUMBER"]
        if matric in existing:
            s = existing[matric]
            s.first_name = record["FIRSTNAME"]
            s.last_name = record["LASTNAME"]
            s.email = record["EMAIL"]
            s.phone = record["PHONE NUMBER"]
            s.department = cls.department
            s.level = cls
            to_update.append(s)
        else:
            to_create.append(
                Student(
                    matric_no=matric,
                    first_name=record["FIRSTNAME"],
                    last_name=record["LASTNAME"],
                    email=record["EMAIL"],
                    phone=record["PHONE NUMBER"],
                    department=cls.department,
                    level=cls,
                )
            )

    with transaction.atomic():
        if to_create:
            Student.objects.bulk_create(to_create, batch_size=250)
        if to_update:
            Student.objects.bulk_update(
                to_update,
                [
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                    "department",
                    "level",
                ],
                batch_size=250,
            )
    return {"created": len(to_create), "updated": len(to_update)}


# Map for the bulk upload dispatcher (POST /api/uploads/bulk/)
BULK_HANDLERS = {
    "departments": upload_departments,
    "halls": upload_halls,
    "courses": upload_courses,
}
