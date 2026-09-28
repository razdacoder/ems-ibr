"""upload_class_students: a class's student CSV."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from ems.models import Student
from ems.upload_handlers import UploadError, upload_class_students

from .helpers import make_class

HEADER = "MATRIC NUMBER,FIRSTNAME,LASTNAME,EMAIL,PHONE NUMBER\n"


def csv_file(body):
    return SimpleUploadedFile("students.csv", (HEADER + body).encode(), content_type="text/csv")


class UploadClassStudentsTests(TestCase):
    def setUp(self):
        self.cls = make_class(0)

    def test_keeps_matric_numbers_exact_when_the_file_has_a_blank_row(self):
        # Regression: one blank cell made pandas read the column as floats, so
        # 2520320002 was stored as "2520320002.0" and printed that way on
        # attendance sheets and the hall directory.
        body = (
            "2520320002,Ada,Obi,ada@example.com,08031234567\n"
            ",,,,\n"
            "2520320003,Bola,Ade,bola@example.com,\n"
        )

        upload_class_students(csv_file(body), self.cls)

        self.assertEqual(
            sorted(Student.objects.values_list("matric_no", flat=True)),
            ["2520320002", "2520320003"],
        )

    def test_keeps_the_leading_zero_on_phone_numbers(self):
        upload_class_students(csv_file("2520320002,Ada,Obi,ada@example.com,08031234567\n"), self.cls)

        self.assertEqual(Student.objects.get().phone, "08031234567")

    def test_keeps_leading_zeros_on_matric_numbers(self):
        upload_class_students(csv_file("0012345678,Ada,Obi,ada@example.com,0803\n"), self.cls)

        self.assertEqual(Student.objects.get().matric_no, "0012345678")

    def test_enrols_students_in_the_class_and_its_department(self):
        result = upload_class_students(
            csv_file("2520320002,Ada,Obi,ada@example.com,0803\n"), self.cls
        )

        student = Student.objects.get()
        self.assertEqual(result, {"created": 1, "updated": 0})
        self.assertEqual((student.level, student.department), (self.cls, self.cls.department))

    def test_uploading_again_updates_instead_of_duplicating(self):
        upload_class_students(csv_file("2520320002,Ada,Obi,ada@example.com,0803\n"), self.cls)

        result = upload_class_students(
            csv_file("2520320002,Adaeze,Obi,ada@example.com,0803\n"), self.cls
        )

        self.assertEqual(result, {"created": 0, "updated": 1})
        self.assertEqual(Student.objects.get().first_name, "Adaeze")

    def test_rejects_duplicate_matric_numbers_in_one_file(self):
        body = "2520320002,Ada,Obi,a@example.com,0803\n2520320002,Bola,Ade,b@example.com,0805\n"

        with self.assertRaisesMessage(UploadError, "Duplicate matric numbers"):
            upload_class_students(csv_file(body), self.cls)
        self.assertFalse(Student.objects.exists())

    def test_rejects_a_file_missing_required_columns(self):
        bad = SimpleUploadedFile("s.csv", b"MATRIC NUMBER,FIRSTNAME\n2520320002,Ada\n")

        with self.assertRaisesMessage(UploadError, "Missing required columns"):
            upload_class_students(bad, self.cls)

    def test_rejects_a_file_with_no_matric_numbers(self):
        with self.assertRaisesMessage(UploadError, "No student rows"):
            upload_class_students(csv_file(",Ada,Obi,ada@example.com,0803\n"), self.cls)


class SpreadsheetFloatTailTests(TestCase):
    """A CSV saved from Excel can hold "2530710047.0" for 2530710047."""

    def setUp(self):
        self.cls = make_class(0)

    def test_strips_the_float_tail_from_matric_and_phone_numbers(self):
        upload_class_students(
            csv_file("2530710047.0,Ada,Obi,ada@example.com,8031234567.0\n"), self.cls
        )

        student = Student.objects.get()
        self.assertEqual(student.matric_no, "2530710047")
        self.assertEqual(student.phone, "8031234567")

    def test_a_float_tail_reupload_updates_the_same_student(self):
        upload_class_students(csv_file("2530710047,Ada,Obi,ada@example.com,\n"), self.cls)
        upload_class_students(csv_file("2530710047.0,Ada,Obi,new@example.com,\n"), self.cls)

        self.assertEqual(Student.objects.get().email, "new@example.com")

    def test_x_and_x_dot_0_in_one_file_are_duplicates(self):
        body = "2530710047,Ada,Obi,a@example.com,\n2530710047.0,Ada,Obi,a@example.com,\n"

        with self.assertRaises(UploadError):
            upload_class_students(csv_file(body), self.cls)

    def test_a_single_student_save_is_cleaned_too(self):
        student = Student.objects.create(
            first_name="Ada", last_name="Obi", matric_no="2530710047.0",
            email="a@example.com", department=self.cls.department, level=self.cls,
            phone="8031234567.00",
        )

        student.refresh_from_db()
        self.assertEqual((student.matric_no, student.phone), ("2530710047", "8031234567"))


class CleanNumberTextTests(TestCase):
    def test_only_an_all_digit_value_with_a_zero_decimal_changes(self):
        from ems.identifiers import clean_number_text

        cases = {
            "2530710047.0": "2530710047",
            " 2530710047.00 ": "2530710047",
            "0012345678": "0012345678",
            "ND/2023/001": "ND/2023/001",
            "20.5": "20.5",
            "": "",
            None: "",
        }
        for raw, expected in cases.items():
            self.assertEqual(clean_number_text(raw), expected, raw)
