import re

from rest_framework import serializers

from ems.models import SystemSettings

_HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class SystemSettingsSerializer(serializers.ModelSerializer):
    # Accept a file on write; expose an absolute URL on read.
    logo = serializers.ImageField(
        write_only=True, required=False, allow_null=True
    )
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = SystemSettings
        fields = [
            "id",
            "session",
            "semester",
            "has_timetable",
            "institution_name",
            "institution_short_name",
            "institution_address",
            "exam_heading",
            "contact_email",
            "contact_phone",
            "logo",
            "logo_url",
            "brand_color",
        ]
        read_only_fields = ["id", "has_timetable"]

    def validate_brand_color(self, value):
        v = (value or "").strip()
        if v and not _HEX_COLOR.match(v):
            raise serializers.ValidationError(
                "Enter a hex colour like #7C3AED."
            )
        return v

    def get_logo_url(self, obj):
        if not obj.logo:
            return None
        url = obj.logo.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url

    def validate_session(self, value):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Session is required.")
        return v

    def validate_semester(self, value):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Semester is required.")
        return v
