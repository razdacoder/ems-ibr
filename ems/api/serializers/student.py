from rest_framework import serializers

from ems.api.exceptions import Conflict
from ems.models import Class, SeatArrangement, Student


class StudentSerializer(serializers.ModelSerializer):
    class_id = serializers.PrimaryKeyRelatedField(
        queryset=Class.objects.all(),
        source="level",
        write_only=True,
    )
    department = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id",
            "first_name",
            "last_name",
            "matric_no",
            "email",
            "phone",
            "department",
            "level",
            "class_id",
        ]
        read_only_fields = ["id", "department", "level"]

    def get_department(self, obj):
        if obj.department_id is None:
            return None
        return {
            "id": obj.department_id,
            "name": obj.department.name,
            "slug": obj.department.slug,
        }

    def get_level(self, obj):
        if obj.level_id is None:
            return None
        return {"id": obj.level_id, "name": obj.level.name}

    def validate_first_name(self, value):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("First name is required.")
        return v

    def validate_last_name(self, value):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("Last name is required.")
        return v

    def validate_matric_no(self, value):
        matric = (value or "").strip().upper()
        if not matric:
            raise serializers.ValidationError("Matric number is required.")
        qs = Student.objects.filter(matric_no=matric)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                f"Student with matric number '{matric}' already exists."
            )
        return matric

    def create(self, validated_data):
        cls = validated_data.pop("level")
        student = Student.objects.create(
            level=cls, department=cls.department, **validated_data
        )
        cls.size = Student.objects.filter(level=cls, department=cls.department).count()
        cls.save(update_fields=["size"])
        return student


def assert_student_deletable(student: Student) -> None:
    if SeatArrangement.objects.filter(student=student).exists():
        raise Conflict(
            "Cannot delete this student: seat arrangements reference them. "
            "Clear the allocation first."
        )
