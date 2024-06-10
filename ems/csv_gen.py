import csv

from django.http import HttpRequest, HttpResponse

from .models import TimeTable


def export_department_timetable(request: HttpRequest) -> HttpResponse:
    department = request.user.department
    filename = f'{department.name}-Timetable.csv'
    timetables = TimeTable.objects.filter(class_obj__department=department)
    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename={filename}'},
    )
    writer = csv.writer(response)
    writer.writerow(["Date", "Level", "Exam Type" "Course Code", "Course Title", "Period"])
    for timetable in timetables:
        writer.writerow([timetable.date.strftime('%A %d, %B %Y'), timetable.class_obj.name, timetable.course.exam_type, timetable.course.code, timetable.course.name, timetable.period])

    return response





