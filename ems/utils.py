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
    SeatArrangement
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
        if item['name'].endswith('II') or item['name'].endswith('2'):
            return True
    return False


# Split courses into AM And PM periods respectively bases on exam type
def split_course(courses):
    AM_courses, PM_courses = [], []
    for course in courses:
        if course['exam_type'] == "PBE":
            if check_course_period(course):
                PM_courses.append(course)
            else:
                AM_courses.append(course)
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

##########################################################################################
################# Seat Allocation ########################################################
##########################################################################################


def allocate_students_to_seats(students, rows, cols, max_attempts=10000):
    if not students:  # Check if students list is empty
        return {}, students, 0  # Return all students as unplaced with 0% placement

    seats = [[None for _ in range(cols)] for _ in range(rows)]
    student_positions = {student['name']: None for student in students}

    def is_valid_position(student_name, row, col):
        course = next(student['course']
                      for student in students if student['name'] == student_name)
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                      (0, 1), (1, -1), (1, 0), (1, 1)]
        for dr, dc in directions:
            r, c = row + dr, col + dc
            if 0 <= r < rows and 0 <= c < cols and seats[r][c]:
                adjacent_student = next(
                    student for student in students if student['name'] == seats[r][c])
                if adjacent_student['course'] == course:
                    return False
        return True

    def try_place_student(student_index):
        student = students[student_index]
        for _ in range(100):  # Try 100 random positions
            row, col = random.randint(0, rows-1), random.randint(0, cols-1)
            if not seats[row][col] and is_valid_position(student['name'], row, col):
                seats[row][col] = student['name']
                student_positions[student['name']] = (row, col)
                return True
        return False

    # Shuffle students to add randomness to the allocation
    random.shuffle(students)
    for student_index in range(len(students)):
        if not try_place_student(student_index):
            # Place failed, stop trying further
            pass

    # Convert positions to sequential seat numbers
    def index_to_seat(row, col):
        # Convert row and column to a sequential seat number (1-based)
        return row * cols + col + 1

    seat_positions = {}
    unplaced_students = []

    for student, position in student_positions.items():
        if position is None:
            unplaced_students.append(student)
        else:
            row, col = position
            if row is not None and col is not None:
                seat_positions[student] = index_to_seat(row, col)
            else:
                unplaced_students.append(student)

    # Calculate the percentage of placed students
    placed_count = len(seat_positions)
    total_students = len(students)
    percentage_placed = (placed_count / total_students) * \
        100 if total_students > 0 else 0

    # Print debug information
    print(f"Total students: {total_students}")
    print(f"Placed students count: {placed_count}")
    print(f"Percentage placed: {percentage_placed:.2f}%")

    if percentage_placed >= 75:
        return seat_positions, unplaced_students, percentage_placed
    else:
        return {}, unplaced_students, percentage_placed


def print_seating_arrangement(students, rows, cols, date, period, hall_id):
    result = allocate_students_to_seats(students, rows, cols)
    if result is None:
        print("Error: allocate_students_to_seats returned None.")
        return

    seat_positions, unplaced_students, percentage_placed = result

    print(f"Percentage of students placed: {percentage_placed:.2f}%")

    if seat_positions:
        # Group students by course
        courses = sorted(set(student['course'] for student in students))
        course_groups = {course: [] for course in courses}
        for student, seat in seat_positions.items():
            course = next(s['course']
                          for s in students if s['name'] == student)
            cls_id = next(s['cls_id']
                          for s in students if s['name'] == student)
            course_groups[course].append((student, seat, cls_id))

        # Print sorted by course and create SeatArrangement objects
        print("\nSeating Arrangement:")
        for course in courses:
            print(f"\n{course}:")
            arrangements = []
            for student, seat, cls_id in sorted(course_groups[course], key=lambda x: x[0]):
                arrangements.append(
                    SeatArrangement(
                        date=date,
                        period=period,
                        student_matric_no=student,
                        seat_number=seat,
                        hall=Hall.objects.get(id=hall_id),
                        course=Course.objects.filter(code=course).first(),
                        cls=Class.objects.get(id=cls_id)
                    )
                )
                print(f"{student}: {seat}")
            SeatArrangement.objects.bulk_create(arrangements)

    # Group and sort unplaced students by course
    unplaced_by_course = {}
    for student in unplaced_students:
        course = next(s['course'] for s in students if s['name'] == student)
        cls_id = next(s['cls_id'] for s in students if s['name'] == student)
        if course not in unplaced_by_course:
            unplaced_by_course[course] = []
        unplaced_by_course[course].append((student, cls_id))

    # Print unplaced students sorted by course and create SeatArrangement objects
    if unplaced_students:
        print("\nUnplaced Students:")
        for course in sorted(unplaced_by_course.keys()):
            print(f"\n{course}:")
            arrangements = []
            for student, cls_id in sorted(unplaced_by_course[course]):
                arrangements.append(
                    SeatArrangement(
                        date=date,
                        period=period,
                        student_matric_no=student,
                        hall=Hall.objects.get(id=hall_id),
                        course=Course.objects.filter(code=course).first(),
                        cls=Class.objects.get(id=cls_id)
                    )
                )
                print(student)
            SeatArrangement.objects.bulk_create(arrangements)


def generate_seat_allocation(rows: int, cols: int, students):
    random.seed(0)
    # Ensure the total number of students does not exceed rows * cols
    if len(students) > rows * cols:
        print(
            f"Error: Too many students for the given hall capacity of {rows * cols} seats.")
    else:
        # Print the seating arrangement
        print_seating_arrangement(students, rows, cols)


def get_student_number(dep_slug, cls, num):
    student_number = ""
    if cls.name.startswith("N"):
        student_number += "N/"
    elif cls.name.startswith("P"):
        student_number += "PN/"
    else:
        student_number += "H/"
    student_number += f"{dep_slug}/{num:04}"
    return student_number
