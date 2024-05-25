import random
from .models import TimeTable, Hall, Distribution, DistributionItem



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



def get_total_no_seats(halls):
    sum = 0
    for hall in halls:
        sum += hall.capacity

    return sum


def get_total_no_seats_needed(timetables):
    sum = 0
    for timetable in timetables:
        sum += timetable.class_obj.size
    return sum

def convert_hall_to_dict(halls):
    halls_dict = []
    for hall in halls:
        hall_dict = {
            "id": hall.id,
            "name": hall.name,
            "capacity": hall.capacity,
            "max_students": hall.max_students,
            "min_courses": hall.min_courses,
            "classes": []
        }
        halls_dict.append(hall_dict)
    return halls_dict

def make_schedules(timetables):
    tt = []
    for timetable in timetables:
        tt.append({"id": timetable.id, 'class': timetable.class_obj.name,
                  "course": timetable.course.code, "size": timetable.class_obj.size})
    random.shuffle(tt)
    return tt

def is_course_in_hall(hall, course_code):
    if len(hall["classes"]) == 0:
        return False
    for cls in hall["classes"]:
        if cls["course"] == course_code:
            return True
    return False


def distribute_classes_to_halls(timetables, halls):
    class_schedules = make_schedules(timetables=timetables)
    results = []
    for hall in halls:
        for schedule in class_schedules:
            if is_course_in_hall(hall, schedule["course"]) or len(hall["classes"]) == hall["min_courses"] or schedule["size"] == 0:
                pass
            else:
                number_of_students = hall["max_students"]
                if number_of_students >= schedule["size"]:
                    number_of_students = schedule["size"]
                if schedule["size"] - number_of_students < 5:
                    number_of_students = schedule["size"]

                res = {"id": schedule["id"], "class": schedule["class"], "course": schedule["course"],
                       "student_range": number_of_students}
                hall["classes"].append(res)
                hall["working_capacity"] -= number_of_students
                schedule["size"] -= number_of_students
    for hall in halls:
        if len(hall["classes"]) == 0:
            pass
        else:
            results.append(hall)
    return results


def save_to_db(res, date, period):
    for item in res:
        hall = Hall.objects.get(id=item["id"])
        distribution, _ = Distribution.objects.get_or_create(
            hall=hall, date=date, period=period
        )
        for cls in item["classes"]:
            schedule = TimeTable.objects.get(id=cls["id"])
            dist_item, _ = DistributionItem.objects.get_or_create(
                schedule=schedule, no_of_students=cls["student_range"]
            )
            distribution.items.add(dist_item)
        distribution.save()
    print("Done")