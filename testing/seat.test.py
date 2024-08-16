import random


def allocate_seats(hall_rows, hall_columns, students):
    total_seats = hall_rows * hall_columns
    seat_matrix = [[None for _ in range(hall_columns)]
                   for _ in range(hall_rows)]

    # Flatten the student list into a single list
    all_students = []
    for course, student_list in students.items():
        for student in student_list:
            all_students.append((student, course))

    random.shuffle(all_students)

    # Allocate seats
    seat_index = 0
    for i in range(hall_rows):
        for j in range(hall_columns):
            if seat_index < len(all_students):
                seat_matrix[i][j] = all_students[seat_index]
                seat_index += 1

    # Ensure students of the same course are not seated close together
    for i in range(hall_rows):
        for j in range(hall_columns):
            if seat_matrix[i][j] is not None:
                current_student, current_course = seat_matrix[i][j]
                # Check neighbors
                if i > 0 and seat_matrix[i-1][j] is not None and seat_matrix[i-1][j][1] == current_course:
                    swap_with_neighbor(seat_matrix, i, j,
                                       hall_rows, hall_columns)
                if j > 0 and seat_matrix[i][j-1] is not None and seat_matrix[i][j-1][1] == current_course:
                    swap_with_neighbor(seat_matrix, i, j,
                                       hall_rows, hall_columns)

    return seat_matrix


def swap_with_neighbor(seat_matrix, i, j, hall_rows, hall_columns):
    for x in range(hall_rows):
        for y in range(hall_columns):
            if (x != i or y != j) and seat_matrix[x][y] is not None:
                if seat_matrix[x][y][1] != seat_matrix[i][j][1]:
                    seat_matrix[i][j], seat_matrix[x][y] = seat_matrix[x][y], seat_matrix[i][j]
                    return


# Example usage
students = {
    "CourseA": ["StudentA", "StudentA", "StudentA", "StudentA", "StudentA", "StudentA", "StudentA", "StudentA", "StudentA", "StudentA", "StudentA", "StudentA", "StudentA", "StudentA", "StudentA"],
    "CourseB": ["StudentB", "StudentB", "StudentB", "StudentB", "StudentB", "StudentB", "StudentB", "StudentB", "StudentB", "StudentB", "StudentB", "StudentB", "StudentB", "StudentB", "StudentB"],
    "CourseC": ["StudentC", "StudentC", "StudentC", "StudentC", "StudentC", "StudentC", "StudentC", "StudentC", "StudentC", "StudentC", "StudentC", "StudentC", "StudentC", "StudentC", "StudentC"],
    "CourseD": ["StudentD", "StudentD", "StudentD", "StudentD", "StudentD", "StudentD", "StudentD", "StudentD", "StudentD", "StudentD", "StudentD", "StudentD", "StudentD", "StudentD", "StudentD"]
}

hall_rows = 10
hall_columns = 10

seating = allocate_seats(hall_rows, hall_columns, students)

for row in seating:
    print(row)
