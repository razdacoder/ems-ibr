import csv
from datetime import datetime
import io
import zipfile
from django.http import HttpRequest, HttpResponse

from .models import Distribution, TimeTable, SeatArrangement


def export_department_timetable(request: HttpRequest) -> HttpResponse:
    department = request.user.department
    filename = f'{department.name}-Timetable.csv'
    timetables = TimeTable.objects.filter(class_obj__department=department)
    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename={filename}'},
    )
    writer = csv.writer(response)
    writer.writerow(
        ["Date", "Level", "Exam Type" "Course Code", "Course Title", "Period"])
    for timetable in timetables:
        writer.writerow([timetable.date.strftime('%A %d, %B %Y'), timetable.class_obj.name,
                        timetable.course.exam_type, timetable.course.code, timetable.course.name, timetable.period])

    return response


def export_distribution(request: HttpRequest) -> HttpResponse:
    date = request.GET.get("date")
    period = request.GET.get("period")

    if date is None:
        date = TimeTable.objects.values_list(
            "date", flat=True).distinct().order_by("date").first()

    if period is None:
        period = "AM"

    if isinstance(date, str):
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        date_obj = date

    distributions = Distribution.objects.filter(date=date_obj, period=period)

    filename = f"{date_obj.strftime(
        '%A %d, %B %Y')} - {period}-Distribution.csv"

    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
    writer = csv.writer(response)
    writer.writerow(["Hall", "Class Name", "No. Of Students"])
    for distribution in distributions:
        for item in distribution.items.all():
            cls = item.schedule.class_obj
            writer.writerow(
                [distribution.hall.name, f"{cls.department.slug} {cls.name}", item.no_of_students])
    return response


def export_arrangements(request: HttpRequest) -> HttpResponse:
    date = request.GET.get("date")
    period = request.GET.get("period")

    if date is None:
        date = TimeTable.objects.values_list(
            "date", flat=True).distinct().order_by("date").first()
    if period is None:
        period = "AM"

    print(f"Date: {date}, Period: {period}")
    if isinstance(date, str):
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        date_obj = date  #
    # date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    arrangements = SeatArrangement.objects.filter(date=date_obj, period=period)

    # Group arrangements by course and class
    courses = arrangements.values_list(
        'course__name', 'course_id', 'cls__name', 'cls__department__slug').distinct()

    # Create an in-memory zip file
    in_memory_zip = io.BytesIO()

    with zipfile.ZipFile(in_memory_zip, 'w') as zip_file:
        for course_name, course_id, class_name, department_slug in courses:
            # Filter arrangements by course and class
            course_arrangements = arrangements.filter(
                course_id=course_id, cls__name=class_name)

            # Create a filename for the CSV
            filename = f"{department_slug}-{class_name}-{course_name}-{
                date_obj.strftime('%A %d, %B %Y')}-{period}-Seating-Arrangement.csv"

            # Create an in-memory CSV file
            csv_file = io.StringIO()
            writer = csv.writer(csv_file)

            # Write the headers
            writer.writerow(['Date', 'Student Name', 'Student Matric No', 'Course Title',
                            'Course Code', 'Venue', 'Period',  'Seat Number'])

            # Write the data rows
            for arrangement in course_arrangements:
                writer.writerow([
                    arrangement.date,
                    f"{arrangement.student.first_name} {arrangement.student.last_name}",
                    arrangement.student.matric_no,
                    arrangement.course.name,
                    arrangement.course.code,
                    arrangement.hall.name,
                    arrangement.period,
                    arrangement.seat_number,
                ])

            # Add the CSV file to the zip archive
            zip_file.writestr(filename, csv_file.getvalue())

    # Prepare the zip file for download
    in_memory_zip.seek(0)
    response = HttpResponse(in_memory_zip, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="seating_arrangements.zip"'

    return response
