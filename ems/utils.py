import os
import random
import shutil
import zipfile

import pandas as pd  # type: ignore
from django.conf import settings

from .models import (
    Class,
    Course,
    Department,
    Distribution,
    DistributionItem,
    Hall,
    TimeTable,
)


def get_new_period(cls, course):
    if course.exam_type == "CBE":
        return "AM"
    if cls.name.split(" ")[1] == "I":
        return "AM"
    else:
        return "PM"


################################################################################################################################################################

# Get Halls to memory location
def get_halls():
    """To get all Halls into memory location"""
    return [{"id": hall.id, "name": hall.name, "capacity": hall.capacity} for hall in Hall.objects.all()]


# Get courses to memory location
def get_courses():
    """To get courses based on classes object"""
    return [
        {
            "id": course.id,
            "code": course.code,
            "exam_type": course.exam_type,
            "classes": [
                {
                    "id": cls.id,
                    "name": cls.name,
                    "size": cls.size
                } for cls in Class.objects.filter(courses__code=course.code)
            ]
        } for course in Course.objects.all()
    ]


# Save timetable to DB
def save_to_timetable_db(schedules):
    """Save schedule into the timetable in DB"""
    timetables = []
    for schedule in schedules:
        for cls in schedule['course']['classes']:
            timetables.append(
                TimeTable(
                    course=Course.objects.get(id=schedule['course']['id']),
                    class_obj=Class.object.get(id=cls['id']),
                    date=schedule['date'],
                    period=schedule['period']
                )
            )
    TimeTable.objects.bulk_create(timetables)


# Check for the Class type to detect AM or PM courses (ND1, PND1, HND1 = "AM" ND2, PND2, HND2 = "PM")
def check_course_period(course):
    for item in course['classes']:
        if item['name'].endswith('II') or item['name'].endswith('2'):
            return True
    return False


# Split courses into AM And PM periods respectively bases on exam type
def split_course(courses):
    AM_courses, PM_courses = [], []
    for course in courses:
        if course['exam_type'] == "PBE" and check_course_period(course):
            PM_courses.append(course)
        else:
            AM_courses.append(course)
    return (AM_courses, PM_courses)


# Helper function to check if a class is scheduled on a given date
def is_class_scheduled(course, date, Schedules):
    for cls in course['classes']:
        for schedule in Schedules:
            if schedule["date"] == date and cls in schedule["course"]["classes"]:
                return True
    return False


# Helper function to check if timetable can still be scheduled based on the number of seats remaining
def can_continue(date, seat_remaining, courses, Schedules):
    for course in courses:
        Seat_Required = sum([Class["size"] for Class in course["classes"]])
        if seat_remaining >= Seat_Required and not is_class_scheduled(course, date, Schedules):
            return True
    return False


# Helper function to get total available seats per period
def get_total_seats(Halls):
    return int(sum([Hall["capacity"] * 0.9 for Hall in Halls]))


# Check for CBE Schedule
def check_for_CBE(schedules, date):
    schedules_date = filter(
        lambda schedule: schedule['date'] == date, schedules)
    for schedule in schedules_date:
        if schedule['course']['exam_type'] == "CBE":
            return True
    return False


# Get the next valid course to schedule
def get_next_course(date, seat_remaining, courses, Schedules):
    for course in courses:
        if 'classes' in course:
            print(
                f"Skipping course with id {course['id']} as it has no 'classes' key.")
            continue
        Seat_Required = sum([cls["size"] for cls in course["classes"]])
        if seat_remaining >= Seat_Required and all(not is_class_scheduled(cls, date, Schedules) for cls in course["classes"]):
            return course
    return None


# Function to generate the timetable and save it to the DB
def generate(dates, courses_AM, courses_PM, Halls):
    # Initialize schedules list
    Schedules = []

    # Loop through the dates
    for Date in dates:
        Total_Seats_AM = get_total_seats(Halls)
        Total_Seats_PM = get_total_seats(Halls)

        Course = get_next_course(
            Date, Total_Seats_AM, courses_AM, Schedules)
        if Course is None:
            break
        # While there are still seats available and courses to add
        while Total_Seats_AM > 0 and len(courses_AM) > 0:

            print("Numbers of Schedule: ", len(Schedules))
            print("Total Seat AM: ", Total_Seats_AM)
            print("Course AM: ", len(courses_AM))
            print("Selected COurses: ", Course)
            if Course['exam_type'] == "CBE":
                print("Old Schedule: ", len(Schedules))
                if not check_for_CBE(Schedules, Date):
                    Schedule = {"course": Course, "date": Date, "period": "AM"}
                    Schedules.append(Schedule)
                    print("New Schedule: ", len(Schedules))
                    courses_AM.remove(Course)
                    print("Course AM: ", len(courses_AM))
            else:
                if not can_continue(Date, Total_Seats_AM, courses_AM, Schedules):
                    print("Cannot continue with AM scheduling")
                    break
                else:
                    print("I am Here")
                    Seat_Required = sum([Class["size"]
                                        for Class in Course["classes"]])
                    print("Seat Required AM: ", Seat_Required)
                    if Total_Seats_AM >= Seat_Required and not is_class_scheduled(Course, Date, Schedules):
                        print("Hiiiiiiiiiiiiii")
                        Schedule = {"course": Course,
                                    "date": Date, "period": "AM"}
                        Schedules.append(Schedule)
                        print("Schedule: ", len(Schedules))
                        Total_Seats_AM -= Seat_Required
                        print("Total Seat AM: ", Total_Seats_AM)
                        courses_AM.remove(Course)
                        print("Course AM: ", len(courses_AM))
        print("\nSEGMENT BETWEEN AM AND PM SCHEDULES\n")
        while Total_Seats_PM > 0 and len(courses_PM) > 0:
            if not can_continue(Date, Total_Seats_PM, courses_PM, Schedules):
                print("Cannot continue with AM scheduling")
                break
            else:
                print("Total Seat PM: ", Total_Seats_PM)
                print("Course PM: ", len(courses_PM))
                print("Course Selected: ", Course)
                Seat_Required = sum([Class["size"]
                                    for Class in Course["classes"]])
                print("Seat Required PM: ", Seat_Required)
                if Total_Seats_PM >= Seat_Required and not is_class_scheduled(Course, Date, Schedules):
                    Schedule = {"course": Course, "date": Date, "period": "PM"}
                    Schedules.append(Schedule)
                    Total_Seats_PM -= Seat_Required
                    print("Total Seat PM: ", Total_Seats_PM)
                    courses_PM.remove(Course)
                    print("Course PM: ", len(courses_PM))

    save_to_timetable_db(Schedules)


################################################################################################################################################################

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
            new_tt.append(TimeTable(course=nc, date=day,
                          period=period, class_obj=cls))
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
                            class_obj = Class.objects.get(
                                name=class_name, department__slug=department_name)
                            process_class_course_csv(class_path, class_obj)
                        except Class.DoesNotExist:
                            print(
                                f"Class {class_name} in department {department_name} does not exist in the database.")


def process_department_class_file(extracted_dir):
    department_class_path = os.path.join(extracted_dir, 'classes')
    if os.path.isdir(department_class_path):
        for department_name in os.listdir(department_class_path):
            department_path = os.path.join(
                department_class_path, department_name)
            if os.path.isdir(department_path):
                class_file_path = os.path.join(department_path, 'classes.csv')
                if os.path.isfile(class_file_path):
                    try:
                        department = Department.objects.get(
                            slug=department_name)
                        process_department_class_csv(
                            class_file_path, department)
                    except Department.DoesNotExist:
                        print(
                            f"Department {department_name} does not exist in the database.")


def process_class_course_csv(file_path, class_obj):
    file = pd.read_csv(file_path).to_dict()
    for key in file['COURSE CODE']:
        code = file['COURSE CODE'][key]
        name = file['COURSE TITLE'][key]
        exam_type = file['EXAM TYPE'][key]
        course, created = Course.objects.get_or_create(
            name=name, code=code, exam_type=exam_type)
        class_obj.courses.add(course)


def process_department_class_csv(class_file_path, department):
    file = pd.read_csv(class_file_path).to_dict()
    for key in file['Name']:
        Class.objects.update_or_create(
            name=file['Name'][key],
            department=department,
            size=file['Size'][key]
        )
