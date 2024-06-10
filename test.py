# import random

# # Sample data
# Classes = [
#     {"id": 1, "name": "Class I", "size": 30},
#     {"id": 2, "name": "Class II", "size": 25},
#     {"id": 3, "name": "Class III", "size": 35},
#     {"id": 4, "name": "Class IV", "size": 20},
#     {"id": 5, "name": "Class V", "size": 30},
#     {"id": 6, "name": "Class VI", "size": 25},
#     {"id": 7, "name": "Class VII", "size": 35},
#     {"id": 8, "name": "Class VIII", "size": 20}
# ]

# Courses = [
#     {"id": 1, "code": "CSE101", "exam_type": "PBE", "classes": [Classes[0], Classes[1]]},
#     {"id": 2, "code": "MTH102", "exam_type": "CBE", "classes": [Classes[2]]},
#     {"id": 3, "code": "PHY103", "exam_type": "PBE", "classes": [Classes[0], Classes[2]]},
#     {"id": 4, "code": "CSE202", "exam_type": "PBE", "classes": [Classes[3], Classes[4]]},
#     {"id": 5, "code": "MTH203", "exam_type": "CBE", "classes": [Classes[5]]},
#     {"id": 6, "code": "PHY204", "exam_type": "PBE", "classes": [Classes[3], Classes[5]]},
#     {"id": 7, "code": "CSE303", "exam_type": "PBE", "classes": [Classes[6], Classes[7]]},
#     {"id": 8, "code": "MTH304", "exam_type": "CBE", "classes": [Classes[7]]},
# ]

# Halls = [
#     {"id": 1, "name": "Hall 1", "capacity": 100},
#     {"id": 2, "name": "Hall 2", "capacity": 120},
#     {"id": 3, "name": "Hall 3", "capacity": 150},
#     {"id": 4, "name": "Hall 4", "capacity": 100}
# ]

# Dates = ["2024-06-10", "2024-06-11", "2024-06-12", "2024-06-13", "2024-06-14"]


# # Initialize schedules list
# Schedules = []

# # Step 1: Get data
# Courses_To_Add = Courses.copy()

# # Step 2: Loop through dates
# for Date in Dates:
#     # Calculate total seats available (90% of total capacity)
#     Total_Seats_AM = sum([Hall["capacity"] * 0.9 for Hall in Halls]) // 2
#     Total_Seats_PM = Total_Seats_AM
    
#     # While there are still seats available and courses to add
#     while Total_Seats_AM >= 0 and Total_Seats_PM >= 0 and len(Courses_To_Add) > 0:
#         # Pick a course at random
#         Course = random.choice(Courses_To_Add)
        
#         # Step 4: Calculate seat required
#         Seat_Required = sum([Class["size"] for Class in Course["classes"]])
        
#         # Step 5: Check if total seats available
#         if Total_Seats_AM >= Seat_Required:
#             # Step 6: Allocate course with date and period
#             Schedule = {"course": Course, "date": Date, "period": "AM"}
#             Schedules.append(Schedule)
            
#             # Step 7: Remove seat required from total seats
#             Total_Seats_AM -= Seat_Required
            
#             # Step 8: Remove course from schedules list
#             Courses_To_Add.remove(Course)
#         elif Total_Seats_PM >= Seat_Required:
#             # Step 6: Allocate course with date and period
#             Schedule = {"course": Course, "date": Date, "period": "PM"}
#             Schedules.append(Schedule)
            
#             # Step 7: Remove seat required from total seats
#             Total_Seats_PM -= Seat_Required
            
#             # Step 8: Remove course from schedules list
#             Courses_To_Add.remove(Course)
    
#     # Step 9: Move to next date
#     Total_Seats_AM = sum([Hall["capacity"] * 0.9 for Hall in Halls]) // 2
#     Total_Seats_PM = Total_Seats_AM

# print(Schedules)

import random

# Sample data
Classes = [
    {"id": 1, "name": "Class I", "size": 30},
    {"id": 2, "name": "Class II", "size": 25},
    {"id": 3, "name": "Class III", "size": 35},
    {"id": 4, "name": "Class IV", "size": 20},
    {"id": 5, "name": "Class V", "size": 30},
    {"id": 6, "name": "Class VI", "size": 25},
    {"id": 7, "name": "Class VII", "size": 35},
    {"id": 8, "name": "Class VIII", "size": 20},
    {"id": 9, "name": "Class IX", "size": 28},
    {"id": 10, "name": "Class X", "size": 32},
    {"id": 11, "name": "Class XI", "size": 27},
    {"id": 12, "name": "Class XII", "size": 22},
    {"id": 13, "name": "Class XIII", "size": 33},
    {"id": 14, "name": "Class XIV", "size": 26},
    {"id": 15, "name": "Class XV", "size": 31},
]

# Sample data with more courses
Courses = [
    {"id": 1, "code": "CSE101", "exam_type": "PBE", "classes": [Classes[0], Classes[1]]},
    {"id": 2, "code": "MTH102", "exam_type": "CBE", "classes": [Classes[2]]},
    {"id": 3, "code": "PHY103", "exam_type": "PBE", "classes": [Classes[0], Classes[2]]},
    {"id": 4, "code": "CSE202", "exam_type": "PBE", "classes": [Classes[3], Classes[4]]},
    {"id": 5, "code": "MTH203", "exam_type": "CBE", "classes": [Classes[5]]},
    {"id": 6, "code": "PHY204", "exam_type": "PBE", "classes": [Classes[3], Classes[5]]},
    {"id": 7, "code": "CSE303", "exam_type": "PBE", "classes": [Classes[6], Classes[7]]},
    {"id": 8, "code": "MTH304", "exam_type": "CBE", "classes": [Classes[7]]},
    {"id": 9, "code": "CSE401", "exam_type": "PBE", "classes": [Classes[8], Classes[9]]},
    {"id": 10, "code": "MTH402", "exam_type": "CBE", "classes": [Classes[10]]},
    {"id": 11, "code": "PHY403", "exam_type": "PBE", "classes": [Classes[8], Classes[10]]},
    {"id": 12, "code": "CSE501", "exam_type": "PBE", "classes": [Classes[11], Classes[12]]},
    {"id": 13, "code": "MTH502", "exam_type": "CBE", "classes": [Classes[13]]},
    {"id": 14, "code": "PHY503", "exam_type": "PBE", "classes": [Classes[11], Classes[13]]},
    {"id": 15, "code": "CSE601", "exam_type": "PBE", "classes": [Classes[14]]},
]

Halls = [
    {"id": 1, "name": "Hall 1", "capacity": 100},
    {"id": 2, "name": "Hall 2", "capacity": 120},
    {"id": 3, "name": "Hall 3", "capacity": 150},
    {"id": 4, "name": "Hall 4", "capacity": 100},
    {"id": 5, "name": "Hall 5", "capacity": 130},
]


Dates = ["2024-06-10", "2024-06-11", "2024-06-12", "2024-06-13", "2024-06-14", "2024-06-15", "2024-06-16", "2024-06-17", "2024-06-18", "2024-06-19", "2024-06-20"]

# Initialize schedules list
Schedules = []

# Helper function to check if a class is scheduled on a given date
def is_class_scheduled(class_obj, date):
    for schedule in Schedules:
        if schedule["date"] == date and class_obj in schedule["course"]["classes"]:
            return True
    return False

# Step 1: Get data
Courses_To_Add = Courses.copy()

# Helper function to get total available seats per period
def get_total_seats():
    return sum([Hall["capacity"] * 0.9 for Hall in Halls]) // 2

# Step 2: Loop through dates
for Date in Dates:
    Total_Seats_AM = get_total_seats()
    Total_Seats_PM = get_total_seats()
    
    # While there are still seats available and courses to add
    while (Total_Seats_AM > 0 or Total_Seats_PM > 0) and len(Courses_To_Add) > 0:
        # Pick a course at random
        Course = random.choice(Courses_To_Add)
        
        # Step 4: Calculate seat required
        Seat_Required = sum([Class["size"] for Class in Course["classes"]])
        
        # Step 5: Check if total seats available and no class has an exam on the same date
        if Total_Seats_AM >= Seat_Required and all(not is_class_scheduled(cls, Date) for cls in Course["classes"]):
            # Step 6: Allocate course with date and period
            Schedule = {"course": Course, "date": Date, "period": "AM"}
            Schedules.append(Schedule)
            
            # Step 7: Remove seat required from total seats
            Total_Seats_AM -= Seat_Required
            
            # Step 8: Remove course from schedules list
            Courses_To_Add.remove(Course)
        elif Total_Seats_PM >= Seat_Required and all(not is_class_scheduled(cls, Date) for cls in Course["classes"]):
            # Step 6: Allocate course with date and period
            Schedule = {"course": Course, "date": Date, "period": "PM"}
            Schedules.append(Schedule)
            
            # Step 7: Remove seat required from total seats
            Total_Seats_PM -= Seat_Required
            
            # Step 8: Remove course from schedules list
            Courses_To_Add.remove(Course)
        else:
            # If the course cannot be scheduled, move to the next date/period
            break

print(Schedules)

