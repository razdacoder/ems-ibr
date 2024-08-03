import csv
from datetime import datetime

from django.http import HttpRequest, HttpResponse

from .models import Distribution, TimeTable


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


def export_distribution(request: HttpRequest, date: str, period: str) -> HttpResponse:
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
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
            writer.writerow([distribution.hall.name, f"{cls.department.slug} {
                            cls.name}", item.no_of_students])
    return response
