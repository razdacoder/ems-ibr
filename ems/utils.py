import os
import random
import shutil
import zipfile

import pandas as pd  # type: ignore
from django.conf import settings
from django.db.models import Prefetch

from .models import (
    Class,
    Course,
    Department,
    Distribution,
    DistributionItem,
    Hall,
    TimeTable,
)

################################################################################################################################################################

# Get Halls to memory location


def get_halls():
    """To get all Halls into memory location"""
    return [{"id": hall.id, "name": hall.name, "capacity": hall.capacity} for hall in Hall.objects.all()]


# Get courses to memory location
def get_courses():
    """To get courses based on classes object"""
    courses = Course.objects.prefetch_related(
        Prefetch('courses', queryset=Class.objects.select_related('department'))
    ).all()

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
                } for cls in course.courses.all()
            ]
        } for course in courses
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
                    class_obj=Class.objects.get(id=cls['id']),
                    date=schedule['date'],
                    period=schedule['period']
                )
            )
    TimeTable.objects.bulk_create(timetables)


# Check for the Class type to detect AM or PM courses (ND1, PND1, HND1 = "AM" ND2, PND2, HND2 = "PM") for only PBE courses
def check_course_period(course):
    for item in course['classes']:
        if item['name'].endswith('I') or item['name'].endswith('1'):
            return True
    return False


# Split courses into AM And PM periods respectively bases on exam type
def split_course(courses):
    AM_courses, PM_courses = [], []
    for course in courses:
        if course['exam_type'] == "PBE":
            if check_course_period(course):
                AM_courses.append(course)
            else:
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


# Helper function to check if timetable can still be scheduled based on the number of seats remaining
def can_continue(date, seat_remaining, courses, Schedules):
    for course in courses:
        Seat_Required = sum([Class["size"] for Class in course["classes"]])
        if seat_remaining >= Seat_Required and not is_class_scheduled(course, date, Schedules) and not check_for_CBE(Schedules, date):
            return True
    return False


def can_continue_PM(date, seat_remaining, courses, Schedules):
    for course in courses:
        Seat_Required = sum([Class["size"] for Class in course["classes"]])
        if seat_remaining >= Seat_Required and not is_class_scheduled(course, date, Schedules):
            return True
    return False


def filter_courses(date, seat_remaining, courses, schedules):
    eligible_courses = []
    for course in courses:
        seat_required = sum(cls["size"] for cls in course["classes"])
        if seat_remaining >= seat_required and not is_class_scheduled(course, date, schedules):
            eligible_courses.append(course)
    return eligible_courses


# Get the next valid course to schedule
def get_next_course(date, seat_remaining, courses, Schedules):
    courses_to_select = filter_courses(
        date, seat_remaining, courses, Schedules)
    return random.choice(courses_to_select)


# Function to generate the timetable and save it to the DB
def generate(dates, courses_AM, courses_PM, Halls):
    # Initialize schedules list
    Schedules = []
    # Loop through the dates
    for Date in dates:
        Total_Seats_AM = get_total_seats(Halls)
        Total_Seats_PM = get_total_seats(Halls)

        AM_scheduling = True
        # While there are still seats available and courses to add
        while AM_scheduling:
            if not can_continue(Date, Total_Seats_AM, courses_AM, Schedules):
                AM_scheduling = False
            Course = get_next_course(
                Date, Total_Seats_AM, courses_AM, Schedules)
            if Course['exam_type'] == "CBE":
                if not check_for_CBE(Schedules, Date):
                    Schedule = {"course": Course, "date": Date, "period": "AM"}
                    Schedules.append(Schedule)
                    courses_AM.remove(Course)
            else:
                Seat_Required = sum([Class["size"]
                                    for Class in Course["classes"]])
                if Total_Seats_AM >= Seat_Required and not is_class_scheduled(Course, Date, Schedules):
                    Schedule = {"course": Course,
                                "date": Date, "period": "AM"}
                    Schedules.append(Schedule)
                    Total_Seats_AM -= Seat_Required
                    courses_AM.remove(Course)
                    if Total_Seats_AM == 0:
                        AM_scheduling = False
                    if len(filter_courses(Date, Total_Seats_AM, courses_AM, Schedules)) == 0:
                        AM_scheduling = False
                        #  Schedule PM Courses
        PM_scheduling = True
        while PM_scheduling:
            if not can_continue_PM(Date, Total_Seats_PM, courses_PM, Schedules):
                PM_scheduling = False
            else:
                Course = get_next_course(
                    Date, Total_Seats_PM, courses_PM, Schedules)
                Seat_Required = sum([Class["size"]
                                    for Class in Course["classes"]])
                if Total_Seats_PM >= Seat_Required and not is_class_scheduled(Course, Date, Schedules):
                    Schedule = {"course": Course, "date": Date, "period": "PM"}
                    Schedules.append(Schedule)
                    Total_Seats_PM -= Seat_Required
                    courses_PM.remove(Course)
                    if Total_Seats_PM == 0:
                        PM_scheduling = False
                    if len(filter_courses(Date, Total_Seats_PM, courses_PM, Schedules)) == 0:
                        PM_scheduling = False
    # Bulk upload schedules to timetable Db
    save_to_timetable_db(Schedules)


################################################################################################################################################################


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
