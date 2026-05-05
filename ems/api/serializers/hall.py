from rest_framework import serializers

from ems.models import Hall


class HallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hall
        fields = [
            "id",
            "name",
            "capacity",
            "max_students",
            "min_courses",
            "rows",
            "columns",
        ]
        read_only_fields = ["id"]

    def validate_name(self, value):
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("Hall name is required.")
        qs = Hall.objects.filter(name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                f"Hall '{name}' already exists."
            )
        return name

    def _positive(self, value, field):
        if value is None or value < 0:
            raise serializers.ValidationError(
                f"{field} must be a non-negative integer."
            )
        return value

    def validate_capacity(self, v):
        return self._positive(v, "Capacity")

    def validate_max_students(self, v):
        return self._positive(v, "Max students")

    def validate_min_courses(self, v):
        return self._positive(v, "Min courses")

    def validate_rows(self, v):
        return self._positive(v, "Rows")

    def validate_columns(self, v):
        return self._positive(v, "Columns")
