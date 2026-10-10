from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from tenancy.models import PlatformAdmin, PlatformAuditLog


class PlatformAdminSerializer(serializers.ModelSerializer):
    """What ``me/`` and sign in return about the signed in admin."""

    class Meta:
        model = PlatformAdmin
        fields = ["id", "email", "name", "role"]


class PlatformAdminListSerializer(serializers.ModelSerializer):
    """An admin as Owners see them on the admins page."""

    totp_enrolled = serializers.SerializerMethodField()
    invite_pending = serializers.SerializerMethodField()

    class Meta:
        model = PlatformAdmin
        fields = [
            "id",
            "email",
            "name",
            "role",
            "is_active",
            "totp_enrolled",
            "invite_pending",
            "last_login",
            "created_at",
        ]

    def get_totp_enrolled(self, obj):
        return obj.totp_confirmed_at is not None

    def get_invite_pending(self, obj):
        return not obj.has_usable_password()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)


class CodeSerializer(serializers.Serializer):
    challenge = serializers.CharField()
    code = serializers.CharField(max_length=10)


class InviteAdminSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(max_length=255)
    role = serializers.ChoiceField(choices=PlatformAdmin.Role.choices)

    def validate_email(self, value):
        value = value.strip().lower()
        if PlatformAdmin.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A platform admin with this email already exists.")
        return value


class UpdateAdminSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    role = serializers.ChoiceField(choices=PlatformAdmin.Role.choices, required=False)
    is_active = serializers.BooleanField(required=False)


class AcceptInviteSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


def check_password_strength(password, admin):
    """``validate_password`` as a DRF field error on ``password``."""
    try:
        validate_password(password, user=admin)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"password": list(exc.messages)})


class _AdminRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformAdmin
        fields = ["id", "name", "email"]


class PlatformAuditLogSerializer(serializers.ModelSerializer):
    admin = _AdminRefSerializer(read_only=True)
    school = serializers.SerializerMethodField()

    class Meta:
        model = PlatformAuditLog
        fields = ["id", "admin", "school", "action", "detail", "ip", "created_at"]

    def get_school(self, obj):
        if obj.school is None:
            return None
        return {"id": obj.school.id, "name": obj.school.name, "slug": obj.school.slug}
