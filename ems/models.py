# Create your models here.
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models


class Faculty(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        verbose_name_plural = "Faculties"
        ordering = ["name"]

    def __str__(self) -> str:
        return str(self.name)


class Department(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=50, unique=True)
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="departments",
    )

    def __str__(self) -> str:
        return str(self.name)


class SystemSettings(models.Model):
    session = models.CharField(
        max_length=200, default="2024/2025", unique=True)
    semester = models.CharField(max_length=100, default="1st Semester")
    has_timetable = models.BooleanField(default=False)

    # Institution branding — shown in the UI beside the app logo and printed
    # on exported documents.
    institution_name = models.CharField(max_length=255, blank=True, default="")
    institution_short_name = models.CharField(
        max_length=50, blank=True, default="")
    institution_address = models.TextField(blank=True, default="")
    exam_heading = models.CharField(max_length=255, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=50, blank=True, default="")
    logo = models.ImageField(upload_to="branding/", null=True, blank=True)
    # Primary brand colour as a hex string (e.g. "#7C3AED"); blank = default theme.
    brand_color = models.CharField(max_length=9, blank=True, default="")

    def __str__(self):
        return str(f"{self.session} ' - ' {self.semester}")


def _default_excluded_weekdays():
    return [6]


def _default_class_period_overrides():
    return {}


def _default_cbe_faculty_groups():
    return {}


# Kept only so historical migrations can import them by name.
def _default_seating_patterns():
    return ["checkerboard", "diagonal", "sequential"]


SEAT_PATTERN_CHOICES = (
    ("checkerboard", "Checkerboard (strict spacing, ~50% capacity)"),
    ("sequential", "Sequential (full capacity, adjacency-only spacing)"),
)


class GenerationConstraints(models.Model):
    """Singleton row holding admin-tunable generation knobs."""

    cbe_autosplit_threshold = models.PositiveIntegerField(default=9000)
    cbe_fullday_threshold = models.PositiveIntegerField(default=4500)
    cbe_daily_cap_per_period = models.PositiveIntegerField(default=4500)

    # Number of buckets a large CBE course splits into, and the
    # faculty-slug → group-number mapping that drives the split.
    cbe_group_count = models.PositiveIntegerField(default=2)
    cbe_faculty_groups = models.JSONField(default=_default_cbe_faculty_groups)
    pbe_hall_utilization = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.90
    )
    # Seat pattern drives effective hall capacity at every stage (timetable
    # seat-budgeting, distribution packing, allocation placement).
    #   * checkerboard → ~50% of grid, students never within 1 cell of each other
    #   * sequential   → full grid, only direct adjacency is blocked
    seat_pattern = models.CharField(
        max_length=20, choices=SEAT_PATTERN_CHOICES, default="checkerboard"
    )
    excluded_weekdays = models.JSONField(default=_default_excluded_weekdays)

    # Map of class-name → "AM" or "PM". Applies to every department that uses
    # that name (e.g. "Level 100" sets AM/PM for every department's Level 100).
    # Missing/blank names default to AM. CBE courses always go AM regardless.
    class_period_overrides = models.JSONField(default=_default_class_period_overrides)

    remainder_merge_threshold = models.PositiveIntegerField(default=5)

    placement_success_threshold_pct = models.PositiveIntegerField(default=60)

    configured_at = models.DateTimeField(null=True, blank=True)
    configured_by = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Generation constraints"
        verbose_name_plural = "Generation constraints"

    def __str__(self):
        return (
            f"GenerationConstraints (configured: "
            f"{'yes' if self.configured_at else 'no'})"
        )


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.SUPER_ADMIN)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SA", "Super Admin"
        DATA_OFFICER = "DO", "Data Officer"
        FACULTY_OFFICER = "FO", "Faculty Officer"
        EXAM_COMMITTEE = "ECM", "Exam Committee Member"

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, null=True, blank=True
    )
    # Admin-side role. Null means a department officer (scoped to ``department``).
    role = models.CharField(
        max_length=4, choices=Role.choices, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def is_super_admin(self) -> bool:
        return bool(self.is_superuser or self.role == self.Role.SUPER_ADMIN)

    @property
    def can_manage_data(self) -> bool:
        """Super admins and data officers manage uploaded data entities."""
        return bool(self.is_super_admin or self.role == self.Role.DATA_OFFICER)

    @property
    def can_manage_faculties(self) -> bool:
        return bool(self.is_super_admin or self.role == self.Role.FACULTY_OFFICER)

    @property
    def is_committee(self) -> bool:
        """Any admin-side role — the exam-committee baseline (dashboard + export)."""
        return self.role in {
            self.Role.SUPER_ADMIN,
            self.Role.DATA_OFFICER,
            self.Role.FACULTY_OFFICER,
            self.Role.EXAM_COMMITTEE,
        }


class Course(models.Model):
    COURSE_TYPE = (("PBE", "PBE"), ("CBE", "CBE"))
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    exam_type = models.CharField(
        max_length=50, default="PBE", choices=COURSE_TYPE)

    def __str__(self) -> str:
        return f"{self.name} - {self.code}"


class Class(models.Model):
    name = models.CharField(max_length=25, null=True, blank=True)
    courses = models.ManyToManyField(Course, related_name="courses")
    department = models.ForeignKey(
        Department, related_name="class_dep", on_delete=models.CASCADE
    )
    size = models.IntegerField()
    # Optional override for the VISA short code. Blank => auto-derived from
    # ``name`` (see ems.directory.derive_visa_code).
    visa_code = models.CharField(max_length=50, blank=True, default="")

    @property
    def full_label(self) -> str:
        """Class name prefixed with its department code, e.g. ``"AC ND II"``.

        Bare class names like ``"ND II"`` are identical across departments, so
        every display/export of a class should carry the department code.
        Skips the prefix when the name already starts with the code.
        """
        dept = getattr(self, "department", None)
        code = (dept.slug.upper() if dept and dept.slug else "").strip()
        name = (self.name or "").strip()
        if code and not name.upper().startswith(code):
            return f"{code} {name}".strip()
        return name

    @property
    def visa_label(self) -> str:
        from ems.directory import derive_visa_code

        if self.visa_code.strip():
            return self.visa_code.strip()
        # The program is usually the department code, so fold it into the name
        # before deriving (e.g. dept "AC" + "ND II" -> "AC ND II" -> "AC II").
        # Skip if the name already starts with the code to avoid doubling.
        dept = getattr(self, "department", None)
        code = (dept.slug.upper() if dept and dept.slug else "").strip()
        name = self.name or ""
        if code and not name.upper().startswith(code):
            name = f"{code} {name}".strip()
        return derive_visa_code(name)

    def __str__(self) -> str:
        return f"{self.name} - {self.department.name}"


class Hall(models.Model):
    name = models.CharField(max_length=255)
    capacity = models.IntegerField()
    max_students = models.IntegerField(default=0)
    min_courses = models.IntegerField(default=0)
    rows = models.IntegerField()
    columns = models.IntegerField()

    def __str__(self) -> str:
        return str(self.name)


PERIOD = (('AM', 'AM'), ('PM', 'PM'))


class TimeTable(models.Model):

    course = models.ForeignKey(
        Course, related_name="timetable_course", on_delete=models.CASCADE)
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE,
                                  related_name="timetable_class")
    period = models.CharField(max_length=50, choices=PERIOD)
    date = models.DateField()

    def __str__(self) -> str:
        return f"{self.class_obj.department.name} | {self.course.code} | {self.date} | {self.period}"


class DistributionItem(models.Model):
    schedule = models.ForeignKey(TimeTable, on_delete=models.CASCADE)
    no_of_students = models.IntegerField()


class Distribution(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE)
    items = models.ManyToManyField(DistributionItem)
    date = models.CharField(max_length=15, null=True)
    period = models.CharField(max_length=2, null=True)


class Student(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    matric_no = models.CharField(max_length=15, db_index=True)
    email = models.EmailField()
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    level = models.ForeignKey(Class, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['department', 'level']),
            models.Index(fields=['matric_no', 'department']),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} - {self.matric_no}"


class SeatArrangement(models.Model):
    period = models.CharField(max_length=50, choices=PERIOD)
    date = models.DateField()
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, null=True, blank=True)
    seat_number = models.IntegerField(null=True, blank=True)
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    cls = models.ForeignKey(Class, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.student.matric_no} - {self.seat_number or 'None'} - Course {self.course.code} - Date {self.date} - Period {self.period}"


class AuditLog(models.Model):
    """Append-only system activity trail.

    One row per authenticated mutating request (and per auth event). Written
    by ``ems.middleware.AuditLogMiddleware`` after the response is produced, so
    the recorded ``status_code`` reflects whether the action actually
    succeeded. Read-only at the API; never edited or deleted by app code.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    # Email snapshotted at write time so the trail survives user deletion and
    # captures failed-login attempts (where no user is attached).
    user_email = models.CharField(max_length=254, blank=True, default="")
    action = models.CharField(max_length=255)
    method = models.CharField(max_length=10, blank=True, default="")
    path = models.CharField(max_length=512, blank=True, default="")
    # Resource the action targeted, e.g. "user" / "department", plus its id.
    object_type = models.CharField(max_length=100, blank=True, default="")
    object_id = models.CharField(max_length=64, blank=True, default="")
    status_code = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["object_type", "-created_at"]),
        ]

    def __str__(self) -> str:
        who = self.user_email or "anonymous"
        return f"{who} — {self.action} ({self.created_at:%Y-%m-%d %H:%M})"

    @property
    def succeeded(self) -> bool:
        return self.status_code is not None and 200 <= self.status_code < 400


class BackgroundJob(models.Model):
    """Track status of long-running background tasks"""
    JOB_TYPES = (
        ('timetable', 'Timetable Generation'),
        ('distribution', 'Distribution Generation'),
        ('allocation', 'Seat Allocation'),
    )
    
    STATUSES = (
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )
    
    job_id = models.CharField(max_length=255, unique=True, db_index=True)
    job_type = models.CharField(max_length=50, choices=JOB_TYPES)
    status = models.CharField(max_length=20, choices=STATUSES, default='pending')
    progress = models.IntegerField(default=0)
    total_steps = models.IntegerField(default=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    result_data = models.JSONField(default=dict, blank=True)
    
    # Job-specific parameters
    params = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['job_id']),
            models.Index(fields=['created_by', '-started_at']),
            models.Index(fields=['status', '-started_at']),
        ]
    
    def __str__(self):
        return f"{self.get_job_type_display()} - {self.status} ({self.progress}%)"
    
    @property
    def progress_percentage(self):
        if self.total_steps == 0:
            return 0
        return min(100, int((self.progress / self.total_steps) * 100))
