from rest_framework import serializers

from ems.models import BackgroundJob


class BackgroundJobSerializer(serializers.ModelSerializer):
    progress = serializers.IntegerField(source="progress_percentage", read_only=True)
    job_type_display = serializers.CharField(
        source="get_job_type_display", read_only=True
    )
    created_by_email = serializers.CharField(
        source="created_by.email", read_only=True
    )

    class Meta:
        model = BackgroundJob
        fields = [
            "job_id",
            "job_type",
            "job_type_display",
            "status",
            "progress",
            "started_at",
            "completed_at",
            "error_message",
            "result_data",
            "params",
            "created_by_email",
        ]
        read_only_fields = fields
