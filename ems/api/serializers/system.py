from rest_framework import serializers

from ems.models import SystemSettings


class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = ["id", "session", "semester", "has_timetable"]
        read_only_fields = ["id", "has_timetable"]

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
