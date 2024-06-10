import random
import os
import zipfile
import shutil
import pandas as pd
from django.conf import settings
from .models import Distribution, DistributionItem, Hall, TimeTable, Department, Class, Course


def get_new_period(cls, course):
    if course.exam_type == "CBE":
        return  "AM"
    if cls.name.split(" ")[1] == "I":
        return "AM"
    else:
       return "PM"


def split_courses(courses):
    sc_courses = []
    nc_courses = []
    for course in courses:
        if TimeTable.objects.filter(course__code=course.code).count() < 1:
            nc_courses.append(course)
        else:
            sc_courses.append(course)

    return (sc_courses, nc_courses)



def schedule_prev(courses, cls, dates):
    if len(courses) > 0:
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
    if len(courses) > 0:
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
                hall["capacity"] -= number_of_students
                schedule["size"] -= number_of_students
    for hall in halls:
        if len(hall["classes"]) == 0:
            pass
        else:
            results.append(hall)
    return results


def save_to_db(res, date, period):
    print(res)
    for item in res:
        hall = Hall.objects.get(id=item["id"])
        distribution = Distribution.objects.create(
            hall=hall, date=date, period=period
        )
        for cls in item["classes"]:
            schedule = TimeTable.objects.get(id=cls["id"])
            dist_item = DistributionItem.objects.create(
                schedule=schedule, no_of_students=cls["student_range"]
            )
            distribution.items.add(dist_item)
            distribution.save()
        distribution.save()
    print("Done")


###################################
##### BULK UPLOAD FUNCTION ########
###################################

def handle_uploaded_file(file, upload_type):
    print("File Uploaded Successful")
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_upload')
    print(os.makedirs(temp_dir, exist_ok=True))

    file_path = os.path.join(temp_dir, file.name)
    with open(file_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)

    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    if upload_type == 'courses':
        process_class_course_files(temp_dir)
    elif upload_type == 'classes':
        process_department_class_file(temp_dir)

    os.remove(file_path)
    shutil.rmtree(temp_dir)


def process_class_course_files(extracted_dir):
    class_course_path = os.path.join(extracted_dir, 'class course')
    if os.path.isdir(class_course_path):
        for department_name in os.listdir(class_course_path):
            department_path = os.path.join(class_course_path, department_name)
            if os.path.isdir(department_path):
                for class_file in os.listdir(department_path):
                    class_name, ext = os.path.splitext(class_file)
                    if ext == '.csv':
                        class_path = os.path.join(department_path, class_file)
                        try:
                            class_obj = Class.objects.get(name=class_name, department__slug=department_name)
                            process_class_course_csv(class_path, class_obj)
                        except Class.DoesNotExist:
                            print(f"Class {class_name} in department {department_name} does not exist in the database.")


def process_department_class_file(extracted_dir):
    department_class_path = os.path.join(extracted_dir, 'classes')
    if os.path.isdir(department_class_path):
        for department_name in os.listdir(department_class_path):
            department_path = os.path.join(department_class_path, department_name)
            if os.path.isdir(department_path):
                class_file_path = os.path.join(department_path, 'classes.csv')
                if os.path.isfile(class_file_path):
                    try:
                        department = Department.objects.get(slug=department_name)
                        process_department_class_csv(class_file_path, department)
                    except Department.DoesNotExist:
                        print(f"Department {department_name} does not exist in the database.")


def process_class_course_csv(file_path, class_obj):
    file = df = pd.read_csv(file_path).to_dict()
    for key in file['COURSE CODE']:
        code = file['COURSE CODE'][key]
        name = file['COURSE TITLE'][key]
        exam_type = file['EXAM TYPE'][key]
        course, created = Course.objects.get_or_create(name=name, code=code, exam_type=exam_type)
        class_obj.courses.add(course)


def process_department_class_csv(class_file_path, department):
    file = pd.read_csv(class_file_path).to_dict()
    for key in file['Name']:
        Class.objects.update_or_create(
            name = file['Name'][key],
            department = department,
            size = file['Size'][key]
        )
