import random


def allocate_students_to_seats(students, rows, cols, max_attempts=10000):
    seats = [[None for _ in range(cols)] for _ in range(rows)]
    student_positions = {student['name']: None for student in students}
    attempts = [0]  # use list to allow modification within nested function

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
            return None

    def index_to_seat(row, col):
        # Convert row and column to a sequential seat number (1-based)
        return row * cols + col + 1

    # Convert positions to sequential seat numbers
    seat_positions = {student: index_to_seat(
        row, col) for student, (row, col) in student_positions.items()}
    return seat_positions


def print_seating_arrangement(students, rows, cols):
    solution = allocate_students_to_seats(students, rows, cols)
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

    # Define the number of rows and columns
    rows = 20
    cols = 25

    # Example list of students with their courses
    students = [
        {'name': 'Student1', 'course': 'MTH 414'},
        {'name': 'Student2', 'course': 'CHM 411'},
        {'name': 'Student3', 'course': 'BAM 212'},
        {'name': 'Student4', 'course': 'COM 213'},
        {'name': 'Student5', 'course': 'COM 213'},
        {'name': 'Student6', 'course': 'BAM 212'},
        {'name': 'Student7', 'course': 'COM 213'},
        {'name': 'Student8', 'course': 'BAM 212'},
        {'name': 'Student9', 'course': 'COM 213'},
        {'name': 'Student10', 'course': 'CHM 411'},
        {'name': 'Student11', 'course': 'BAM 212'},
        {'name': 'Student12', 'course': 'MTH 414'},
        {'name': 'Student13', 'course': 'CTE 216'},
        {'name': 'Student14', 'course': 'COM 213'},
        {'name': 'Student15', 'course': 'CTE 216'},
        {'name': 'Student16', 'course': 'COM 213'},
        {'name': 'Student17', 'course': 'CHM 411'},
        {'name': 'Student18', 'course': 'CHM 411'},
        {'name': 'Student19', 'course': 'CTE 216'},
        {'name': 'Student20', 'course': 'MTH 414'},
        {'name': 'Student21', 'course': 'CTE 216'},
        {'name': 'Student22', 'course': 'BAM 212'},
        {'name': 'Student23', 'course': 'BAM 212'},
        {'name': 'Student24', 'course': 'CTE 216'},
        {'name': 'Student25', 'course': 'CHM 411'},
        {'name': 'Student26', 'course': 'BAM 212'},
        {'name': 'Student27', 'course': 'MTH 414'},
        {'name': 'Student28', 'course': 'CTE 216'},
        {'name': 'Student29', 'course': 'MTH 414'},
        {'name': 'Student30', 'course': 'CHM 411'},
        {'name': 'Student31', 'course': 'CHM 411'},
        {'name': 'Student32', 'course': 'COM 213'},
        {'name': 'Student33', 'course': 'BAM 212'},
        {'name': 'Student34', 'course': 'MTH 414'},
        {'name': 'Student35', 'course': 'CHM 411'},
        {'name': 'Student36', 'course': 'CTE 216'},
        {'name': 'Student37', 'course': 'MTH 414'},
        {'name': 'Student38', 'course': 'BAM 212'},
        {'name': 'Student39', 'course': 'BAM 212'},
        {'name': 'Student40', 'course': 'CTE 216'},
        {'name': 'Student41', 'course': 'CTE 216'},
        {'name': 'Student42', 'course': 'CTE 216'},
        {'name': 'Student43', 'course': 'BAM 212'},
        {'name': 'Student44', 'course': 'CHM 411'},
        {'name': 'Student45', 'course': 'MTH 414'},
        {'name': 'Student46', 'course': 'COM 213'},
        {'name': 'Student47', 'course': 'CTE 216'},
        {'name': 'Student48', 'course': 'CTE 216'},
        {'name': 'Student49', 'course': 'CHM 411'},
        {'name': 'Student50', 'course': 'CTE 216'},
        {'name': 'Student51', 'course': 'COM 213'},
        {'name': 'Student52', 'course': 'BAM 212'},
        {'name': 'Student53', 'course': 'CTE 216'},
        {'name': 'Student54', 'course': 'CTE 216'},
        {'name': 'Student55', 'course': 'MTH 414'},
        {'name': 'Student56', 'course': 'BAM 212'},
        {'name': 'Student57', 'course': 'COM 213'},
        {'name': 'Student58', 'course': 'BAM 212'},
        {'name': 'Student59', 'course': 'BAM 212'},
        {'name': 'Student60', 'course': 'CHM 411'},
        {'name': 'Student61', 'course': 'CHM 411'},
        {'name': 'Student62', 'course': 'MTH 414'},
        {'name': 'Student63', 'course': 'COM 213'},
        {'name': 'Student64', 'course': 'COM 213'},
        {'name': 'Student65', 'course': 'CHM 411'},
        {'name': 'Student66', 'course': 'COM 213'},
        {'name': 'Student67', 'course': 'CTE 216'},
        {'name': 'Student68', 'course': 'MTH 414'},
        {'name': 'Student69', 'course': 'BAM 212'},
        {'name': 'Student70', 'course': 'MTH 414'},
        {'name': 'Student71', 'course': 'BAM 212'},
        {'name': 'Student72', 'course': 'CTE 216'},
        {'name': 'Student73', 'course': 'CHM 411'},
        {'name': 'Student74', 'course': 'MTH 414'},
        {'name': 'Student75', 'course': 'MTH 414'},
        {'name': 'Student76', 'course': 'MTH 414'},
        {'name': 'Student77', 'course': 'COM 213'},
        {'name': 'Student78', 'course': 'MTH 414'},
        {'name': 'Student79', 'course': 'MTH 414'},
        {'name': 'Student80', 'course': 'COM 213'},
        {'name': 'Student81', 'course': 'CTE 216'},
        {'name': 'Student82', 'course': 'COM 213'},
        {'name': 'Student83', 'course': 'CTE 216'},
        {'name': 'Student84', 'course': 'CTE 216'},
        {'name': 'Student85', 'course': 'CTE 216'},
        {'name': 'Student86', 'course': 'MTH 414'},
        {'name': 'Student87', 'course': 'BAM 212'},
        {'name': 'Student88', 'course': 'CHM 411'},
        {'name': 'Student89', 'course': 'BAM 212'},
        {'name': 'Student90', 'course': 'CHM 411'},
        {'name': 'Student91', 'course': 'CTE 216'},
        {'name': 'Student92', 'course': 'BAM 212'},
        {'name': 'Student93', 'course': 'COM 213'},
        {'name': 'Student94', 'course': 'COM 213'},
        {'name': 'Student95', 'course': 'BAM 212'},
        {'name': 'Student96', 'course': 'MTH 414'},
        {'name': 'Student97', 'course': 'BAM 212'},
        {'name': 'Student98', 'course': 'MTH 414'},
        {'name': 'Student99', 'course': 'COM 213'},
        {'name': 'Student100', 'course': 'BAM 212'},
        {'name': 'Student101', 'course': 'CTE 216'},
        {'name': 'Student102', 'course': 'CHM 411'},
        {'name': 'Student103', 'course': 'CTE 216'},
        {'name': 'Student104', 'course': 'MTH 414'},
        {'name': 'Student105', 'course': 'BAM 212'},
        {'name': 'Student106', 'course': 'CTE 216'},
        {'name': 'Student107', 'course': 'CHM 411'},
        {'name': 'Student108', 'course': 'CTE 216'},
        {'name': 'Student109', 'course': 'MTH 414'},
        {'name': 'Student110', 'course': 'MTH 414'},
        {'name': 'Student111', 'course': 'MTH 414'},
        {'name': 'Student112', 'course': 'CHM 411'},
        {'name': 'Student113', 'course': 'CTE 216'},
        {'name': 'Student114', 'course': 'MTH 414'},
        {'name': 'Student115', 'course': 'COM 213'},
        {'name': 'Student116', 'course': 'BAM 212'},
        {'name': 'Student117', 'course': 'CHM 411'},
        {'name': 'Student118', 'course': 'CTE 216'},
        {'name': 'Student119', 'course': 'COM 213'},
        {'name': 'Student120', 'course': 'MTH 414'},
        {'name': 'Student121', 'course': 'MTH 414'},
        {'name': 'Student122', 'course': 'CTE 216'},
        {'name': 'Student123', 'course': 'BAM 212'},
        {'name': 'Student124', 'course': 'MTH 414'},
        {'name': 'Student125', 'course': 'CHM 411'},
        {'name': 'Student126', 'course': 'BAM 212'},
        {'name': 'Student127', 'course': 'COM 213'},
        {'name': 'Student128', 'course': 'BAM 212'},
        {'name': 'Student129', 'course': 'BAM 212'},
        {'name': 'Student130', 'course': 'MTH 414'},
        {'name': 'Student131', 'course': 'BAM 212'},
        {'name': 'Student132', 'course': 'COM 213'},
        {'name': 'Student133', 'course': 'CTE 216'},
        {'name': 'Student134', 'course': 'BAM 212'},
        {'name': 'Student135', 'course': 'COM 213'},
        {'name': 'Student136', 'course': 'MTH 414'},
        {'name': 'Student137', 'course': 'MTH 414'},
        {'name': 'Student138', 'course': 'BAM 212'},
        {'name': 'Student139', 'course': 'BAM 212'},
        {'name': 'Student140', 'course': 'MTH 414'},
        {'name': 'Student141', 'course': 'CHM 411'},
        {'name': 'Student142', 'course': 'MTH 414'},
        {'name': 'Student143', 'course': 'BAM 212'},
        {'name': 'Student144', 'course': 'CHM 411'},
        {'name': 'Student145', 'course': 'BAM 212'},
        {'name': 'Student146', 'course': 'CTE 216'},
        {'name': 'Student147', 'course': 'BAM 212'},
        {'name': 'Student148', 'course': 'COM 213'},
        {'name': 'Student149', 'course': 'CTE 216'},
        {'name': 'Student150', 'course': 'BAM 212'},
        {'name': 'Student151', 'course': 'COM 213'},
        {'name': 'Student152', 'course': 'COM 213'},
        {'name': 'Student153', 'course': 'CHM 411'},
        {'name': 'Student154', 'course': 'COM 213'},
        {'name': 'Student155', 'course': 'COM 213'},
        {'name': 'Student156', 'course': 'CTE 216'},
        {'name': 'Student157', 'course': 'CTE 216'},
        {'name': 'Student158', 'course': 'CTE 216'},
        {'name': 'Student159', 'course': 'CHM 411'},
        {'name': 'Student160', 'course': 'CHM 411'},
        {'name': 'Student161', 'course': 'CHM 411'},
        {'name': 'Student162', 'course': 'CHM 411'},
        {'name': 'Student163', 'course': 'BAM 212'},
        {'name': 'Student164', 'course': 'COM 213'},
        {'name': 'Student165', 'course': 'MTH 414'},
        {'name': 'Student166', 'course': 'CTE 216'},
        {'name': 'Student167', 'course': 'BAM 212'},
        {'name': 'Student168', 'course': 'CTE 216'},
        {'name': 'Student169', 'course': 'BAM 212'},
        {'name': 'Student170', 'course': 'BAM 212'},
        {'name': 'Student171', 'course': 'CHM 411'},
        {'name': 'Student172', 'course': 'BAM 212'},
        {'name': 'Student173', 'course': 'CHM 411'},
        {'name': 'Student174', 'course': 'BAM 212'},
        {'name': 'Student175', 'course': 'MTH 414'},
        {'name': 'Student176', 'course': 'MTH 414'},
        {'name': 'Student177', 'course': 'BAM 212'},
        {'name': 'Student178', 'course': 'COM 213'},
        {'name': 'Student179', 'course': 'MTH 414'},
        {'name': 'Student180', 'course': 'CTE 216'},
        {'name': 'Student181', 'course': 'COM 213'},
        {'name': 'Student182', 'course': 'MTH 414'},
        {'name': 'Student183', 'course': 'BAM 212'},
        {'name': 'Student184', 'course': 'COM 213'},
        {'name': 'Student185', 'course': 'COM 213'},
        {'name': 'Student186', 'course': 'CTE 216'},
        {'name': 'Student187', 'course': 'MTH 414'},
        {'name': 'Student188', 'course': 'CTE 216'},
        {'name': 'Student189', 'course': 'CHM 411'},
        {'name': 'Student190', 'course': 'MTH 414'},
        {'name': 'Student191', 'course': 'CHM 411'},
        {'name': 'Student192', 'course': 'CHM 411'},
        {'name': 'Student193', 'course': 'CTE 216'},
        {'name': 'Student194', 'course': 'MTH 414'},
        {'name': 'Student195', 'course': 'BAM 212'},
        {'name': 'Student196', 'course': 'CTE 216'},
        {'name': 'Student197', 'course': 'BAM 212'},
        {'name': 'Student198', 'course': 'MTH 414'},
        {'name': 'Student199', 'course': 'CHM 411'},
        {'name': 'Student200', 'course': 'COM 213'},
        {'name': 'Student201', 'course': 'CTE 216'},
        {'name': 'Student202', 'course': 'CHM 411'},
        {'name': 'Student203', 'course': 'BAM 212'},
        {'name': 'Student204', 'course': 'CTE 216'},
        {'name': 'Student205', 'course': 'CHM 411'},
        {'name': 'Student206', 'course': 'COM 213'},
        {'name': 'Student207', 'course': 'COM 213'},
        {'name': 'Student208', 'course': 'BAM 212'},
        {'name': 'Student209', 'course': 'CTE 216'},
        {'name': 'Student210', 'course': 'MTH 414'},
        {'name': 'Student211', 'course': 'CTE 216'},
        {'name': 'Student212', 'course': 'COM 213'},
        {'name': 'Student213', 'course': 'MTH 414'},
        {'name': 'Student214', 'course': 'MTH 414'},
        {'name': 'Student215', 'course': 'CTE 216'},
        {'name': 'Student216', 'course': 'CTE 216'},
        {'name': 'Student217', 'course': 'BAM 212'},
        {'name': 'Student218', 'course': 'MTH 414'},
        {'name': 'Student219', 'course': 'MTH 414'},
        {'name': 'Student220', 'course': 'CTE 216'},
        {'name': 'Student221', 'course': 'CTE 216'},
        {'name': 'Student222', 'course': 'MTH 414'},
        {'name': 'Student223', 'course': 'BAM 212'},
        {'name': 'Student224', 'course': 'CHM 411'},
        {'name': 'Student225', 'course': 'MTH 414'},
        {'name': 'Student226', 'course': 'CHM 411'},
        {'name': 'Student227', 'course': 'COM 213'},
        {'name': 'Student228', 'course': 'CHM 411'},
        {'name': 'Student229', 'course': 'CTE 216'},
        {'name': 'Student230', 'course': 'MTH 414'}
    ]

    # Ensure the total number of students does not exceed rows * cols
    if len(students) > rows * cols:
        print(
            f"Error: Too many students for the given hall capacity of {rows * cols} seats.")
    else:
        # Print the seating arrangement
        print_seating_arrangement(students, rows, cols)
