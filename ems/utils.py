from .models import TimeTable

def split_courses(courses):
    sc_courses = []
    nc_courses = []
    for course in courses:
        if TimeTable.objects.filter(course__code=course.code).count() < 1:
            nc_courses.append(course)
        else:
            sc_courses.append(course)

    return (sc_courses, nc_courses)