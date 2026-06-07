from django.contrib.auth import authenticate
from rest_framework import serializers

from ems.models import Department, User


class DepartmentRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "slug"]


class UserSerializer(serializers.ModelSerializer):
    department = DepartmentRefSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source="department",
        write_only=True,
        required=False,
        allow_null=True,
    )
    full_name = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_staff",
            "is_active",
            "department",
            "department_id",
            "password",
            "created_at",
        ]
        # ``is_staff`` is derived from ``role`` on save, so it is read-only here.
        read_only_fields = ["id", "created_at", "is_staff"]

    def get_full_name(self, obj):
        first = (obj.first_name or "").strip()
        last = (obj.last_name or "").strip()
        return (f"{first} {last}").strip() or obj.email

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        # Any admin-side role is staff; a roleless user is a department officer.
        user.is_staff = bool(user.role)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if "role" in validated_data:
            instance.is_staff = bool(instance.role)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    """Email + password login. Mirrors DRF's AuthTokenSerializer but uses email."""

    email = serializers.EmailField()
    password = serializers.CharField(
        style={"input_type": "password"}, trim_whitespace=False
    )

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=password,
        )
        if not user:
            raise serializers.ValidationError(
                "Invalid email or password.", code="authorization"
            )
        if not user.is_active:
            raise serializers.ValidationError(
                "This account is disabled.", code="authorization"
            )
        attrs["user"] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, write_only=True)
