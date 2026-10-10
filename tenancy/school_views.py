"""Schools and plans in the console, ``/api/platform/`` (spec 0003, children 0004, 0005).

Creating a school saves it with its primary domain and queues provisioning,
which builds the schema in the background. Every transition locks the
``School`` row and records a ``PlatformAuditLog`` row.
"""
from datetime import date

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework import generics, status
from rest_framework.response import Response

from ems.api.exceptions import Conflict
from ems.api.pagination import DefaultPagination
from tenancy import audit
from tenancy.auth import PlatformTokenAuthentication
from tenancy.models import Domain, Plan, School
from tenancy.permissions import IsPlatformOwner, IsPlatformStaff
from tenancy.serializers import (
    CreateSchoolSerializer,
    PlanSerializer,
    SchoolDetailSerializer,
    SchoolListSerializer,
    UpdateSchoolSerializer,
)
from tenancy.slugs import schema_name_for
from tenancy.tasks import provision_school
from tenancy.views import PlatformView


def schools():
    """Every school but the public schema's own row."""
    return (
        School.objects.exclude(schema_name=get_public_schema_name())
        .select_related("plan", "created_by")
        .prefetch_related("domains")
    )


def _cannot(action, school):
    return Conflict(f"Cannot {action} a school that is {school.get_status_display().lower()}.")


def _first_admin(school):
    """Whether the first admin has joined, and when their open invite expires."""
    if school.status not in School.LIVE_STATUSES:
        return None
    with schema_context(school.schema_name):
        from ems import invites

        joined = invites.user_exists(school.first_admin_email)
        pending = (
            invites.open_invites()
            .filter(email=school.first_admin_email)
            .values_list("expires_at", flat=True)
            .first()
        )
    return {"joined": joined, "invite_expires_at": None if joined else pending}


def _detail(school, code=status.HTTP_200_OK):
    data = SchoolDetailSerializer(
        school, context={"first_admin": _first_admin(school)}
    ).data
    return Response(data, status=code)


def _queue_provisioning(school):
    school_id = school.pk
    transaction.on_commit(lambda: provision_school.delay(school_id))


class SchoolListView(generics.ListAPIView):
    authentication_classes = [PlatformTokenAuthentication]
    serializer_class = SchoolListSerializer
    pagination_class = DefaultPagination

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsPlatformOwner()]
        return [IsPlatformStaff()]

    def get_queryset(self):
        queryset = schools().order_by("-created_at", "-id")
        params = self.request.query_params
        if params.get("status") in School.Status.values:
            queryset = queryset.filter(status=params["status"])
        if q := params.get("q", "").strip():
            queryset = queryset.filter(Q(name__icontains=q) | Q(slug__icontains=q))
        return queryset

    def post(self, request):
        serializer = CreateSchoolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        slug = data["slug"]
        try:
            with transaction.atomic():
                school = School.objects.create(
                    **data,
                    schema_name=schema_name_for(slug),
                    status=School.Status.PROVISIONING,
                    provisioning_started_at=timezone.now(),
                    created_by=request.user,
                )
                Domain.objects.create(
                    domain=f"{slug}.{settings.PLATFORM_BASE_DOMAIN}",
                    tenant=school,
                    is_primary=True,
                )
                audit.record(
                    request, "school_created", school, slug=slug, plan=school.plan.code
                )
                _queue_provisioning(school)
        except IntegrityError:
            # Another Owner took the slug between the check and the save.
            return Response(
                {
                    "detail": "Validation failed.",
                    "errors": {"slug": ["This address is already taken."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return _detail(schools().get(pk=school.pk), status.HTTP_202_ACCEPTED)


class SchoolDetailView(PlatformView):
    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsPlatformOwner()]
        return [IsPlatformStaff()]

    def get(self, request, pk):
        return _detail(get_object_or_404(schools(), pk=pk))

    def patch(self, request, pk):
        """Edit details, plan, overrides or dates. The slug never changes."""
        with transaction.atomic():
            school = get_object_or_404(schools().select_for_update(of=("self",)), pk=pk)
            serializer = UpdateSchoolSerializer(school, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            changes = _apply(school, serializer.validated_data)
            if changes:
                school.save(update_fields=list(changes))
                audit.record(request, "school_updated", school, changes=changes)
        return _detail(schools().get(pk=pk))


def _audit_value(value):
    if isinstance(value, Plan):
        return value.code
    if isinstance(value, date):
        return value.isoformat()
    return value


def _apply(obj, data):
    """Set the fields whose value changes; ``{field: [old, new]}`` for the audit."""
    changes = {}
    for field, value in data.items():
        old = getattr(obj, field)
        if old != value:
            changes[field] = [_audit_value(old), _audit_value(value)]
            setattr(obj, field, value)
    return changes


class SchoolRetryView(PlatformView):
    """Drop whatever the failed attempt left behind and provision again."""

    permission_classes = [IsPlatformOwner]

    def post(self, request, pk):
        with transaction.atomic():
            school = get_object_or_404(schools().select_for_update(of=("self",)), pk=pk)
            if school.status != School.Status.FAILED:
                raise _cannot("retry", school)
            # Only ever a schema that never went live: a failed school was
            # never active (spec 0003, child 0004, key invariants).
            school.drop_schema()
            previous_error = school.provisioning_error
            school.status = School.Status.PROVISIONING
            school.provisioning_started_at = timezone.now()
            school.provisioning_error = ""
            school.save(
                update_fields=["status", "provisioning_started_at", "provisioning_error"]
            )
            audit.record(
                request, "school_provisioning_retried", school, previous_error=previous_error
            )
            _queue_provisioning(school)
        return _detail(school, status.HTTP_202_ACCEPTED)


class SchoolResendInviteView(PlatformView):
    """Email the first admin a new link; any earlier link stops working."""

    def post(self, request, pk):
        from ems import invites
        from ems.models import User

        with transaction.atomic():
            school = get_object_or_404(schools().select_for_update(of=("self",)), pk=pk)
            if school.status != School.Status.ACTIVE:
                raise Conflict(
                    "Invites can only be resent for an active school. This one is "
                    f"{school.get_status_display().lower()}."
                )
            with schema_context(school.schema_name):
                if invites.user_exists(school.first_admin_email):
                    raise Conflict("The first admin has already joined.")
                invites.invite(
                    school,
                    email=school.first_admin_email,
                    role=User.Role.SUPER_ADMIN,
                    name=school.first_admin_name,
                )
            audit.record(
                request, "school_invite_resent", school, email=school.first_admin_email
            )
        return Response(status=status.HTTP_202_ACCEPTED)


def plans():
    """Every plan with how many schools are on it (the public row isn't one)."""
    on_plan = (
        schools()
        .filter(plan=OuterRef("pk"))
        .order_by()
        .values("plan")
        .annotate(n=Count("pk"))
        .values("n")
    )
    return Plan.objects.annotate(school_count=Coalesce(Subquery(on_plan), 0))


class PlanListView(PlatformView):
    """Every plan, offered ones first. Plans are deactivated, never deleted."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsPlatformOwner()]
        return [IsPlatformStaff()]

    def get(self, request):
        return Response(PlanSerializer(plans().order_by("-is_active", "name"), many=True).data)

    def post(self, request):
        serializer = PlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            plan = serializer.save()
            audit.record(request, "plan_created", code=plan.code, plan=serializer.data)
        return Response(
            PlanSerializer(plans().get(pk=plan.pk)).data, status=status.HTTP_201_CREATED
        )


class PlanDetailView(PlatformView):
    permission_classes = [IsPlatformOwner]

    def patch(self, request, pk):
        """Edit any field but the code; ``is_active`` false stops offering it."""
        with transaction.atomic():
            plan = get_object_or_404(Plan.objects.select_for_update(), pk=pk)
            serializer = PlanSerializer(plan, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            changes = _apply(plan, serializer.validated_data)
            if changes:
                plan.save(update_fields=list(changes))
                audit.record(request, "plan_updated", code=plan.code, changes=changes)
        return Response(PlanSerializer(plans().get(pk=pk)).data)
