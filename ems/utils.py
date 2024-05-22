import random
from .models import TimeTable



def get_new_period(cls, course):
    if course.exam_type == "CBE":
        return  "AM"
    if cls.name.split(" ")[1] == "I":
        return "AM"
    else:
       return "PM"

    
    

    return period

def split_courses(courses):
    sc_courses = courses.filter(timetable_course__isnull=False)
    nc_courses = courses.filter(timetable_course__isnull=True)
    return (sc_courses, nc_courses)



def schedule_prev(courses, cls, dates):
    if courses.exists():
        new_tt = []
        for course in courses:
            timetable = TimeTable.objects.filter(course__code=course.code)[0]
            new_tt.append(TimeTable(
                date=timetable.date,
                course=timetable.course,
                class_obj=cls,
                period=timetable.period
            ))
            if timetable.date in dates:
                dates.remove(timetable.date)
        TimeTable.objects.bulk_create(new_tt)


def schedule_next(courses, cls, dates):
    if courses.exists():
        new_tt = []
        for nc in courses:
            day = random.choice(dates)
            period = get_new_period(cls, nc)
            new_tt.append(TimeTable(course=nc, date=day, period=period, class_obj=cls))
            if day in dates:
                dates.remove(day)
        TimeTable.objects.bulk_create(new_tt)