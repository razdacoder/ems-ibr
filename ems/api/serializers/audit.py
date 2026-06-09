from rest_framework import serializers

from ems.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    succeeded = serializers.BooleanField(read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "user_email",
            "user_name",
            "action",
            "method",
            "path",
            "object_type",
            "object_id",
            "status_code",
            "succeeded",
            "ip_address",
            "user_agent",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields

    def get_user_name(self, obj) -> str:
        if obj.user_id and obj.user:
            first = (obj.user.first_name or "").strip()
            last = (obj.user.last_name or "").strip()
            full = f"{first} {last}".strip()
            return full or obj.user.email
        return obj.user_email or "—"
