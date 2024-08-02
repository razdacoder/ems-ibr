import random


def allocate_students_to_seats(students, rows, cols, constraints, max_attempts=100000):
    seats = [[None for _ in range(cols)] for _ in range(rows)]
    student_positions = {student['name']: None for student in students}
    attempts = [0]  # use list to allow modification within nested function

    def is_valid_position(student_name, row, col):
        course = next(student['course']
                      for student in students if student['name'] == student_name)
        min_distance = constraints.get('min_distance', 1)
        directions = [(-d, -d) for d in range(1, min_distance + 1)] + \
                     [(-d, 0) for d in range(1, min_distance + 1)] + \
                     [(-d, d) for d in range(1, min_distance + 1)] + \
                     [(0, -d) for d in range(1, min_distance + 1)] + \
                     [(0, d) for d in range(1, min_distance + 1)] + \
                     [(d, -d) for d in range(1, min_distance + 1)] + \
                     [(d, 0) for d in range(1, min_distance + 1)] + \
                     [(d, d) for d in range(1, min_distance + 1)]
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
        possible_positions = [(row, col) for row in range(rows)
                              for col in range(cols) if not seats[row][col]]
        random.shuffle(possible_positions)
        for row, col in possible_positions:
            if is_valid_position(student['name'], row, col):
                seats[row][col] = student['name']
                student_positions[student['name']] = (row, col)
                return True
        return False

    # Shuffle students to add randomness to the allocation
    random.shuffle(students)
    for student_index in range(len(students)):
        if not try_place_student(student_index):
            return None

    def index_to_seat(row, col):
        # Convert row and column to a sequential seat number (1-based)
        return row * cols + col + 1

    # Convert positions to sequential seat numbers
    seat_positions = {student: index_to_seat(
        row, col) for student, (row, col) in student_positions.items()}
    return seat_positions


def print_seating_arrangement(students, rows, cols, constraints):
    solution = allocate_students_to_seats(students, rows, cols, constraints)
    if solution:
        # Group students by course
        courses = sorted(set(student['course'] for student in students))
        course_groups = {course: [] for course in courses}
        for student, seat in solution.items():
            course = next(s['course']
                          for s in students if s['name'] == student)
            course_groups[course].append((student, seat))

        # Print sorted by course
        for course in courses:
            print(f"\n{course}:")
            for student, seat in course_groups[course]:
                print(f"{student}: {seat}")
    else:
        print("No valid seating arrangement found.")


# Example usage
if __name__ == "__main__":
    random.seed(0)

    # Define the number of rows and columns for different halls
    hall_configurations = [
        {'rows': 10, 'cols': 8, 'constraints': {'min_distance': 1}},   # 80 seats
        {'rows': 15, 'cols': 10, 'constraints': {'min_distance': 2}},  # 150 seats
        {'rows': 20, 'cols': 15, 'constraints': {'min_distance': 3}},  # 300 seats
        {'rows': 25, 'cols': 20, 'constraints': {'min_distance': 4}},  # 500 seats
    ]

    # Example list of students with their courses
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

    # Ensure the total number of students does not exceed rows * cols
    for config in hall_configurations:
        rows, cols, constraints = config['rows'], config['cols'], config['constraints']
        if len(students) > rows * cols:
            print(f"Error: Too many students for the given hall capacity of {
                  rows * cols} seats.")
        else:
            print(f"\nSeating arrangement for hall with {rows} rows and {
                  cols} columns, constraints: {constraints}")
            print_seating_arrangement(students, rows, cols, constraints)
