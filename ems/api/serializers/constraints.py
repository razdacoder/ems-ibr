from rest_framework import serializers

from ems.models import GenerationConstraints

VALID_PERIODS = {"AM", "PM"}


class GenerationConstraintsSerializer(serializers.ModelSerializer):
    configured = serializers.SerializerMethodField()
    configured_by_email = serializers.CharField(
        source="configured_by.email", read_only=True, default=None
    )

    class Meta:
        model = GenerationConstraints
        fields = [
            "id",
            "cbe_autosplit_threshold",
            "cbe_fullday_threshold",
            "cbe_daily_cap_per_period",
            "cbe_group_count",
            "cbe_faculty_groups",
            "pbe_hall_utilization",
            "excluded_weekdays",
            "class_period_overrides",
            "remainder_merge_threshold",
            "placement_success_threshold_pct",
            "configured_at",
            "configured_by",
            "configured_by_email",
            "configured",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "configured_at",
            "configured_by",
            "configured_by_email",
            "configured",
            "updated_at",
        ]

    def get_configured(self, obj):
        return obj.configured_at is not None

    def validate_excluded_weekdays(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of weekday integers.")
        cleaned = []
        for v in value:
            if not isinstance(v, int) or v < 0 or v > 6:
                raise serializers.ValidationError(
                    "Each weekday must be an integer 0–6 (0=Mon, 6=Sun)."
                )
            cleaned.append(v)
        if not cleaned:
            raise serializers.ValidationError(
                "At least one excluded weekday is required."
            )
        return sorted(set(cleaned))

    def validate_pbe_hall_utilization(self, value):
        if value is None or value <= 0 or value > 1:
            raise serializers.ValidationError(
                "Utilization must be greater than 0 and at most 1."
            )
        return value

    def validate_placement_success_threshold_pct(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Must be between 0 and 100.")
        return value

    def validate_cbe_group_count(self, value):
        if value is None or value < 2:
            raise serializers.ValidationError("Must be at least 2.")
        if value > 10:
            raise serializers.ValidationError(
                "Too many groups (max 10). Reduce and try again."
            )
        return value

    def validate_cbe_faculty_groups(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Expected an object mapping faculty slug → group number."
            )
        cleaned: dict[str, int] = {}
        for slug, group in value.items():
            if not isinstance(slug, str) or not slug.strip():
                raise serializers.ValidationError(
                    "Faculty slugs must be non-empty strings."
                )
            try:
                num = int(group)
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    f"Group for '{slug}' must be an integer (got {group!r})."
                )
            if num < 1:
                raise serializers.ValidationError(
                    f"Group for '{slug}' must be ≥ 1."
                )
            cleaned[slug.strip()] = num
        return cleaned

    def validate_class_period_overrides(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Expected an object mapping class name → AM/PM."
            )
        cleaned = {}
        for name, period in value.items():
            if not isinstance(name, str) or not name.strip():
                raise serializers.ValidationError(
                    "Class names must be non-empty strings."
                )
            normalized = (period or "").upper()
            if normalized and normalized not in VALID_PERIODS:
                raise serializers.ValidationError(
                    f"Period for '{name}' must be 'AM' or 'PM' (got '{period}')."
                )
            if normalized:
                cleaned[name.strip()] = normalized
        return cleaned

    def _ensure_positive(self, value, field):
        if value is None or value < 1:
            raise serializers.ValidationError(
                {field: f"{field} must be a positive integer."}
            )

    def validate(self, attrs):
        for field in (
            "cbe_autosplit_threshold",
            "cbe_fullday_threshold",
            "cbe_daily_cap_per_period",
            "remainder_merge_threshold",
        ):
            if field in attrs:
                self._ensure_positive(attrs[field], field)

        # Coherence: fullday ≤ autosplit, daily cap ≤ autosplit
        autosplit = attrs.get(
            "cbe_autosplit_threshold",
            getattr(self.instance, "cbe_autosplit_threshold", None),
        )
        fullday = attrs.get(
            "cbe_fullday_threshold",
            getattr(self.instance, "cbe_fullday_threshold", None),
        )
        if autosplit and fullday and fullday > autosplit:
            raise serializers.ValidationError(
                {
                    "cbe_fullday_threshold": (
                        "Full-day threshold cannot exceed the auto-split threshold."
                    )
                }
            )

        # Faculty-group numbers must fit within the configured group count.
        group_count = attrs.get(
            "cbe_group_count",
            getattr(self.instance, "cbe_group_count", None),
        )
        faculty_groups = attrs.get(
            "cbe_faculty_groups",
            getattr(self.instance, "cbe_faculty_groups", None),
        )
        if group_count and faculty_groups:
            out_of_range = sorted(
                {slug for slug, g in faculty_groups.items() if g > group_count}
            )
            if out_of_range:
                raise serializers.ValidationError(
                    {
                        "cbe_faculty_groups": (
                            f"Group numbers exceed cbe_group_count={group_count}: "
                            f"{', '.join(out_of_range)}."
                        )
                    }
                )
        return attrs
