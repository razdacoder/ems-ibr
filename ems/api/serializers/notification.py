from rest_framework import serializers

from ems.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "link", "data", "created_at", "read_at"]
        read_only_fields = fields
