import random
students = [
    {'name': 'PN/BAM/0001', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0002', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0003', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0004', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0005', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0006', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0007', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0008', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0009', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0010', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0011', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0012', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0013', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0014', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0015', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0016', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0017', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0018', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0019', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0020', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0021', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0022', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0023', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0024', 'course': 'MKT 115'
     },
    {'name': 'PN/BAM/0025', 'course': 'MKT 115'
     },
    {'name': 'N/AGT/0001', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0002', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0003', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0004', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0005', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0006', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0007', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0008', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0009', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0010', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0011', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0012', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0013', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0014', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0015', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0016', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0017', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0018', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0019', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0020', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0021', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0022', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0023', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0024', 'course': 'AGT 112'
     },
    {'name': 'N/AGT/0025', 'course': 'AGT 112'
     },
    {'name': 'H/HMT/0001', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0002', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0003', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0004', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0005', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0006', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0007', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0008', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0009', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0010', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0011', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0012', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0013', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0014', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0015', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0016', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0017', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0018', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0019', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0020', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0021', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0022', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0023', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0024', 'course': 'HMT 311'
     },
    {'name': 'H/HMT/0025', 'course': 'HMT 311'
     },
    {'name': 'N/CS/0001', 'course': 'COM 113'
     },
    {'name': 'N/CS/0002', 'course': 'COM 113'
     },
    {'name': 'N/CS/0003', 'course': 'COM 113'
     },
    {'name': 'N/CS/0004', 'course': 'COM 113'
     },
    {'name': 'N/CS/0005', 'course': 'COM 113'
     },
    {'name': 'N/CS/0006', 'course': 'COM 113'
     },
    {'name': 'N/CS/0007', 'course': 'COM 113'
     },
    {'name': 'N/CS/0008', 'course': 'COM 113'
     },
    {'name': 'N/CS/0009', 'course': 'COM 113'
     },
    {'name': 'N/CS/0010', 'course': 'COM 113'
     },
    {'name': 'N/CS/0011', 'course': 'COM 113'
     },
    {'name': 'N/CS/0012', 'course': 'COM 113'
     },
    {'name': 'N/CS/0013', 'course': 'COM 113'
     },
    {'name': 'N/CS/0014', 'course': 'COM 113'
     },
    {'name': 'N/CS/0015', 'course': 'COM 113'
     },
    {'name': 'N/CS/0016', 'course': 'COM 113'
     },
    {'name': 'N/CS/0017', 'course': 'COM 113'
     },
    {'name': 'N/CS/0018', 'course': 'COM 113'
     },
    {'name': 'N/CS/0019', 'course': 'COM 113'
     },
    {'name': 'N/CS/0020', 'course': 'COM 113'
     },
    {'name': 'N/CS/0021', 'course': 'COM 113'
     },
    {'name': 'N/CS/0022', 'course': 'COM 113'
     },
    {'name': 'N/CS/0023', 'course': 'COM 113'
     },
    {'name': 'N/CS/0024', 'course': 'COM 113'
     },
    {'name': 'N/CS/0025', 'course': 'COM 113'
     }
]


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


def print_seating_arrangement(students, rows, cols):
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
            course_groups[course].append((student, seat))

        # Print sorted by course
        print("\nSeating Arrangement:")
        for course in courses:
            print(f"\n{course}:")
            for student, seat in sorted(course_groups[course], key=lambda x: x[0]):
                print(f"{student}: {seat}")

    # Group and sort unplaced students by course
    unplaced_by_course = {}
    for student in unplaced_students:
        course = next(s['course'] for s in students if s['name'] == student)
        if course not in unplaced_by_course:
            unplaced_by_course[course] = []
        unplaced_by_course[course].append(student)

    # Print unplaced students sorted by course
    if unplaced_students:
        print("\nUnplaced Students:")
        for course in sorted(unplaced_by_course.keys()):
            print(f"\n{course}:")
            for student in sorted(unplaced_by_course[course]):
                print(student)


# Example usage
if __name__ == "__main__":
    random.seed(0)

    # Define the number of rows and columns
    rows = 12
    cols = 10

    # Ensure the total number of students does not exceed rows * cols
    if len(students) > rows * cols:
        print(
            f"Error: Too many students for the given hall capacity of {rows * cols} seats.")
    else:
        # Print the seating arrangement
        print_seating_arrangement(students, rows, cols)
