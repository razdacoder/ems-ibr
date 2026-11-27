from django.utils import timezone
from rest_framework import serializers

from ems.api.serializers.user import DepartmentRefSerializer
from ems.models import Department, Invite, User


class InviteSerializer(serializers.ModelSerializer):
    """An open invite, as the Invites tab lists it."""

    department = DepartmentRefSerializer(read_only=True)
    invited_by = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Invite
        fields = [
            "id",
            "email",
            "role",
            "department",
            "invited_by",
            "expires_at",
            "is_expired",
            "created_at",
        ]

    def get_invited_by(self, obj):
        user = obj.invited_by
        if user is None:
            return None
        name = f"{user.first_name} {user.last_name}".strip()
        return {"id": user.id, "name": name or user.email, "email": user.email}

    def get_is_expired(self, obj):
        return obj.expires_at <= timezone.now()


class CreateInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    # Null is a department officer, who needs a department.
    role = serializers.ChoiceField(
        choices=User.Role.choices, allow_null=True, required=False, default=None
    )
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source="department",
        allow_null=True,
        required=False,
        default=None,
    )

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        if attrs["role"]:
            # Admin side roles aren't scoped to a department.
            attrs["department"] = None
        elif attrs["department"] is None:
            raise serializers.ValidationError(
                {"department_id": ["Pick the department this officer looks after."]}
            )
        return attrs


class AcceptInviteSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    password = serializers.CharField(trim_whitespace=False)
