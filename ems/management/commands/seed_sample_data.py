"""Generate realistic sample CSVs and seed them into the database.

Usage examples
--------------
# Generate CSVs under ./seed_data/ AND load them into the DB (purge first):
python manage.py seed_sample_data --purge

# Only generate CSVs (no DB writes):
python manage.py seed_sample_data --csv-only

# Skip CSV generation, just load existing CSVs from a directory:
python manage.py seed_sample_data --seed-only --output seed_data/

# Smaller scenario for fast tests:
python manage.py seed_sample_data --purge --students 2000

The output directory mirrors the bulk-upload ZIP layout the system already
understands, so you can also zip it and feed it through the bulk upload
endpoint if you prefer that path.
"""

from __future__ import annotations

import csv
import random
import string
from pathlib import Path
from typing import Iterable

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from ems.models import (
    Class,
    Course,
    Department,
    Faculty,
    Hall,
    Student,
)


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

FACULTIES: list[tuple[str, str]] = [
    ("Faculty of Sciences", "FOS"),
    ("Faculty of Engineering", "FOE"),
    ("Faculty of Arts", "FOA"),
    ("Faculty of Health Sciences", "FOH"),
    ("Faculty of Law", "FOL"),
    ("Faculty of Management and Economics", "FME"),
    ("Faculty of Social Sciences", "FSS"),
    ("Faculty of Education", "FED"),
    ("Faculty of Agriculture", "FAG"),
    ("Faculty of Computing", "FOC"),
]

# 8 departments per faculty (80 total). Codes are 3-letter unique slugs.
DEPARTMENTS_BY_FACULTY: dict[str, list[tuple[str, str]]] = {
    "FOS": [
        ("Biology", "BIO"),
        ("Chemistry", "CHM"),
        ("Physics", "PHY"),
        ("Mathematics", "MTH"),
        ("Statistics", "STA"),
        ("Biochemistry", "BCH"),
        ("Microbiology", "MCB"),
        ("Geology", "GEO"),
    ],
    "FOE": [
        ("Civil Engineering", "CVL"),
        ("Mechanical Engineering", "MEC"),
        ("Electrical Engineering", "ELE"),
        ("Chemical Engineering", "CHE"),
        ("Mechatronics Engineering", "MCT"),
        ("Petroleum Engineering", "PET"),
        ("Biomedical Engineering", "BME"),
        ("Industrial Engineering", "IND"),
    ],
    "FOA": [
        ("English", "ENG"),
        ("History", "HIS"),
        ("Linguistics", "LIN"),
        ("Philosophy", "PHL"),
        ("Religious Studies", "REL"),
        ("French", "FRE"),
        ("Theatre Arts", "THA"),
        ("Music", "MUS"),
    ],
    "FOH": [
        ("Medicine", "MED"),
        ("Pharmacy", "PHA"),
        ("Nursing", "NUR"),
        ("Public Health", "PHE"),
        ("Physiotherapy", "PHT"),
        ("Medical Laboratory Sciences", "MLS"),
        ("Dentistry", "DNT"),
        ("Radiography", "RAD"),
    ],
    "FOL": [
        ("Public Law", "PUL"),
        ("Private Law", "PVL"),
        ("Commercial Law", "CML"),
        ("International Law", "ILA"),
        ("Criminology", "CRM"),
        ("Jurisprudence", "JUR"),
        ("Constitutional Law", "CSL"),
        ("Property Law", "PRL"),
    ],
    "FME": [
        ("Accounting", "ACC"),
        ("Economics", "ECO"),
        ("Business Administration", "BUS"),
        ("Marketing", "MKT"),
        ("Finance", "FIN"),
        ("Banking", "BNK"),
        ("Insurance", "INS"),
        ("Public Administration", "PAD"),
    ],
    "FSS": [
        ("Political Science", "POL"),
        ("Sociology", "SOC"),
        ("Psychology", "PSY"),
        ("Mass Communication", "MAS"),
        ("Geography", "GEG"),
        ("Anthropology", "ANT"),
        ("Demography", "DEM"),
        ("Social Work", "SWK"),
    ],
    "FED": [
        ("Educational Management", "EMG"),
        ("Curriculum Studies", "CUR"),
        ("Early Childhood Education", "ECE"),
        ("Adult Education", "ADE"),
        ("Special Education", "SPE"),
        ("Guidance and Counselling", "GAC"),
        ("Library Science", "LIS"),
        ("Physical Education", "PED"),
    ],
    "FAG": [
        ("Crop Science", "CRP"),
        ("Animal Science", "ANS"),
        ("Soil Science", "SOL"),
        ("Agricultural Economics", "AGE"),
        ("Agricultural Extension", "AEX"),
        ("Fisheries", "FIS"),
        ("Forestry", "FOR"),
        ("Horticulture", "HOR"),
    ],
    "FOC": [
        ("Computer Science", "CSC"),
        ("Software Engineering", "SFE"),
        ("Information Technology", "ITC"),
        ("Cyber Security", "CYS"),
        ("Data Science", "DAS"),
        ("Information Systems", "ISY"),
        ("Computer Engineering", "CEN"),
        ("Artificial Intelligence", "AIE"),
    ],
}

CLASS_LEVELS: list[tuple[str, int]] = [
    # (class_name, level_number used for course-code generation)
    ("ND1", 1),
    ("ND2", 2),
    ("HND1", 3),
    ("HND2", 4),
]

# General studies courses (CBE) — shared across most classes.
GENERAL_COURSES: list[tuple[str, str]] = [
    ("GNS 101", "Use of English I"),
    ("GNS 102", "Use of English II"),
    ("GNS 111", "Citizenship Education"),
    ("GNS 121", "Communication Skills"),
    ("GNS 201", "Logic and Critical Thinking"),
    ("GNS 202", "Entrepreneurship Studies"),
    ("GNS 301", "Research Methodology"),
    ("GNS 302", "Nigerian Peoples and Culture"),
    ("GNS 401", "Project Management"),
    ("GNS 402", "Leadership and Ethics"),
]

TITLE_TOPICS = [
    "Foundations",
    "Principles",
    "Methods",
    "Concepts",
    "Theory",
    "Applications",
    "Systems",
    "Design",
    "Analysis",
    "Practice",
    "Research",
    "Topics",
    "Modelling",
    "Techniques",
    "Workshop",
]

FIRST_NAMES = [
    "Adebayo", "Adeola", "Olumide", "Tunde", "Nkem", "Chioma", "Folake",
    "Ngozi", "Bayo", "Wale", "Emeka", "Ifeanyi", "Damilola", "Funke",
    "Bukola", "Kemi", "Yinka", "Sade", "Tobi", "Mojisola", "Seun", "Bisi",
    "Lola", "Tola", "Tope", "Yemi", "Femi", "Bola", "Bode", "Dele",
    "Niyi", "Lekan", "Sola", "Tomi", "Tayo", "Tunji", "Chinedu",
    "Chukwudi", "Obinna", "Amaka", "Ifeoma", "Uche", "Nneka", "Chinyere",
    "Oluwaseun", "Aisha", "Fatima", "Halima", "Zainab", "Hauwa",
]

LAST_NAMES = [
    "Adeyemi", "Okafor", "Eze", "Adesanya", "Aliyu", "Okeke", "Nwosu",
    "Adigun", "Ogundipe", "Bello", "Okonkwo", "Obi", "Olayemi",
    "Akinwande", "Olatunji", "Ojo", "Okoro", "Akinola", "Ogunleye",
    "Adeleke", "Adekunle", "Ojeniyi", "Ogundimu", "Okolie", "Adeniran",
    "Ogunbiyi", "Adesina", "Onifade", "Adekola", "Akinwumi", "Olawumi",
    "Adesoji", "Akinrinola", "Adeyemo", "Ibrahim", "Mohammed", "Yusuf",
    "Sani", "Lawal", "Ahmed", "Suleiman", "Bakare", "Salami", "Hassan",
]


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = (
        "Generate realistic sample CSVs (10 faculties, 80 departments, halls, "
        "courses, classes, students) and seed them into the database."
    )

    # default sizing constants (overridable via flags)
    DEFAULT_HALL_COUNT = 25
    DEFAULT_STUDENTS = 40_000
    COURSES_PER_LEVEL = 12          # available pool per (dept, level)
    CLASS_COURSES_MIN = 8
    CLASS_COURSES_MAX = 14
    GENERAL_PER_CLASS_MIN = 1
    GENERAL_PER_CLASS_MAX = 2
    CLASS_SIZE_MIN = 80
    CLASS_SIZE_MAX = 180

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="seed_data",
            help="Output directory for the generated CSVs (default: seed_data).",
        )
        parser.add_argument(
            "--students",
            type=int,
            default=self.DEFAULT_STUDENTS,
            help="Total number of students to generate (default: 40000).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducibility (default: 42).",
        )
        parser.add_argument(
            "--csv-only",
            action="store_true",
            help="Write CSVs only; do not touch the database.",
        )
        parser.add_argument(
            "--seed-only",
            action="store_true",
            help="Skip CSV writing; load existing CSVs from --output.",
        )
        parser.add_argument(
            "--purge",
            action="store_true",
            help=(
                "Delete existing Faculty/Department/Hall/Course/Class/Student "
                "rows before seeding."
            ),
        )

    # ---- entry point ------------------------------------------------------

    def handle(self, *args, **opts):
        if opts["csv_only"] and opts["seed_only"]:
            raise CommandError("--csv-only and --seed-only are mutually exclusive.")

        random.seed(opts["seed"])
        out = Path(opts["output"]).resolve()

        if not opts["seed_only"]:
            self.stdout.write(self.style.NOTICE(f"Generating CSVs into {out}"))
            self._write_csvs(out, total_students=opts["students"])

        if opts["csv_only"]:
            self.stdout.write(self.style.SUCCESS("CSV generation complete."))
            return

        if opts["purge"]:
            self._purge()

        self.stdout.write(self.style.NOTICE(f"Seeding database from {out}"))
        self._seed_from_csvs(out)
        self.stdout.write(self.style.SUCCESS("Seed complete."))

    # ---- CSV generation ---------------------------------------------------

    def _write_csvs(self, out: Path, total_students: int) -> None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "classes").mkdir(exist_ok=True)
        (out / "class course").mkdir(exist_ok=True)
        (out / "students").mkdir(exist_ok=True)

        # 1. faculties.csv
        self._write_csv(
            out / "faculties.csv",
            ["Name", "Code"],
            [{"Name": name, "Code": code} for name, code in FACULTIES],
        )

        # 2. departments.csv (Faculty Code is non-standard — the seeder reads it)
        departments_rows: list[dict] = []
        all_departments: list[tuple[str, str, str]] = []  # (name, code, faculty_code)
        for fac_code in [c for _, c in FACULTIES]:
            for dept_name, dept_code in DEPARTMENTS_BY_FACULTY[fac_code]:
                departments_rows.append(
                    {
                        "Name": dept_name,
                        "Code": dept_code,
                        "Faculty Code": fac_code,
                    }
                )
                all_departments.append((dept_name, dept_code, fac_code))
        self._write_csv(
            out / "departments.csv",
            ["Name", "Code", "Faculty Code"],
            departments_rows,
        )

        # 3. halls.csv
        halls_rows = self._build_halls(self.DEFAULT_HALL_COUNT)
        self._write_csv(
            out / "halls.csv",
            ["EXAM VENUE", "CAPACITY", "MAX STUDENTS", "MIN COURSES", "ROWS", "COLS"],
            halls_rows,
        )

        # 4. courses.csv — institutional catalog
        catalog: list[dict] = []
        catalog.extend(
            {
                "COURSE CODE": code,
                "COURSE TITLE": title,
                "EXAM TYPE": "CBE",
            }
            for code, title in GENERAL_COURSES
        )
        # Per-department, per-level course pools
        dept_level_pools: dict[tuple[str, int], list[str]] = {}
        for dept_name, dept_code, _ in all_departments:
            for _, level_num in CLASS_LEVELS:
                pool: list[str] = []
                for n in range(1, self.COURSES_PER_LEVEL + 1):
                    code = f"{dept_code} {level_num}{n:02d}"
                    title = self._course_title(dept_name, level_num, n)
                    catalog.append(
                        {
                            "COURSE CODE": code,
                            "COURSE TITLE": title,
                            "EXAM TYPE": "PBE",
                        }
                    )
                    pool.append(code)
                dept_level_pools[(dept_code, level_num)] = pool
        self._write_csv(
            out / "courses.csv",
            ["COURSE CODE", "COURSE TITLE", "EXAM TYPE"],
            catalog,
        )
        course_lookup = {row["COURSE CODE"]: row for row in catalog}

        # 5. classes/<dept_slug>/classes.csv  (sizes scaled to hit total_students)
        students_per_class = self._distribute_class_sizes(
            num_departments=len(all_departments),
            classes_per_dept=len(CLASS_LEVELS),
            total_students=total_students,
        )
        # students_per_class is a flat list aligned to (dept_index * classes_per_dept + class_index)

        # 6. class course/<dept_slug>/<class_name>.csv — pick courses for each class
        # 7. students/<dept_slug>/<class_name>.csv — generate students per class
        all_dept_codes = [d[1] for d in all_departments]
        global_student_counter = 1
        idx = 0
        for dept_name, dept_code, _ in all_departments:
            dept_classes_rows = []
            for class_name, level_num in CLASS_LEVELS:
                size = students_per_class[idx]
                idx += 1
                dept_classes_rows.append({"Name": class_name, "Size": size})

                # class course file
                pool = list(dept_level_pools[(dept_code, level_num)])
                pick_count = random.randint(
                    self.CLASS_COURSES_MIN, self.CLASS_COURSES_MAX
                )
                # Reserve room for general courses
                gen_count = random.randint(
                    self.GENERAL_PER_CLASS_MIN, self.GENERAL_PER_CLASS_MAX
                )
                gen_count = min(gen_count, pick_count - 1) if pick_count else gen_count
                dept_pick = pick_count - gen_count
                dept_pick = max(0, min(dept_pick, len(pool)))
                chosen_dept = random.sample(pool, dept_pick)
                chosen_gen = random.sample(
                    [c for c, _ in GENERAL_COURSES],
                    k=min(gen_count, len(GENERAL_COURSES)),
                )
                chosen = chosen_dept + chosen_gen
                random.shuffle(chosen)

                cc_dir = out / "class course" / dept_code
                cc_dir.mkdir(parents=True, exist_ok=True)
                self._write_csv(
                    cc_dir / f"{class_name}.csv",
                    ["COURSE CODE", "COURSE TITLE", "EXAM TYPE"],
                    [
                        {
                            "COURSE CODE": code,
                            "COURSE TITLE": course_lookup[code]["COURSE TITLE"],
                            "EXAM TYPE": course_lookup[code]["EXAM TYPE"],
                        }
                        for code in chosen
                    ],
                )

                # students file
                students_dir = out / "students" / dept_code
                students_dir.mkdir(parents=True, exist_ok=True)
                rows: list[dict] = []
                for seq in range(1, size + 1):
                    first = random.choice(FIRST_NAMES)
                    last = random.choice(LAST_NAMES)
                    matric = f"{class_name}/{dept_code}/{seq:04d}"
                    email = (
                        f"{first.lower()}.{last.lower()}{global_student_counter}"
                        "@students.school.edu"
                    )
                    phone = "080" + "".join(random.choices(string.digits, k=8))
                    rows.append(
                        {
                            "MATRIC NUMBER": matric,
                            "FIRSTNAME": first,
                            "LASTNAME": last,
                            "EMAIL": email,
                            "PHONE NUMBER": phone,
                        }
                    )
                    global_student_counter += 1
                self._write_csv(
                    students_dir / f"{class_name}.csv",
                    [
                        "MATRIC NUMBER",
                        "FIRSTNAME",
                        "LASTNAME",
                        "EMAIL",
                        "PHONE NUMBER",
                    ],
                    rows,
                )

            cls_dir = out / "classes" / dept_code
            cls_dir.mkdir(parents=True, exist_ok=True)
            self._write_csv(
                cls_dir / "classes.csv", ["Name", "Size"], dept_classes_rows
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"  faculties:   {len(FACULTIES)}\n"
                f"  departments: {len(all_departments)}\n"
                f"  halls:       {len(halls_rows)}\n"
                f"  courses:     {len(catalog)}\n"
                f"  classes:     {len(all_departments) * len(CLASS_LEVELS)}\n"
                f"  students:    {sum(students_per_class)}"
            )
        )

    # ---- DB seeding -------------------------------------------------------

    def _purge(self) -> None:
        self.stdout.write(self.style.WARNING("Purging existing data…"))
        with transaction.atomic():
            Student.objects.all().delete()
            # M2M Class.courses unbinds automatically when classes/courses go
            Class.objects.all().delete()
            Course.objects.all().delete()
            Hall.objects.all().delete()
            Department.objects.all().delete()
            Faculty.objects.all().delete()

    def _seed_from_csvs(self, out: Path) -> None:
        if not out.exists():
            raise CommandError(f"Seed directory {out} does not exist.")

        with transaction.atomic():
            # 1. Faculties
            fac_by_code: dict[str, Faculty] = {}
            for row in self._read_csv(out / "faculties.csv"):
                fac, _ = Faculty.objects.get_or_create(
                    slug=row["Code"].strip().upper(),
                    defaults={"name": row["Name"].strip()},
                )
                fac_by_code[fac.slug] = fac
            self.stdout.write(f"  Faculties: {len(fac_by_code)}")

            # 2. Departments
            dept_by_code: dict[str, Department] = {}
            for row in self._read_csv(out / "departments.csv"):
                fac_code = (row.get("Faculty Code") or "").strip().upper()
                dept, _ = Department.objects.get_or_create(
                    slug=row["Code"].strip().upper(),
                    defaults={
                        "name": row["Name"].strip(),
                        "faculty": fac_by_code.get(fac_code),
                    },
                )
                # Backfill faculty even if dept existed
                if not dept.faculty and fac_code in fac_by_code:
                    dept.faculty = fac_by_code[fac_code]
                    dept.save(update_fields=["faculty"])
                dept_by_code[dept.slug] = dept
            self.stdout.write(f"  Departments: {len(dept_by_code)}")

            # 3. Halls
            hall_count = 0
            for row in self._read_csv(out / "halls.csv"):
                Hall.objects.get_or_create(
                    name=row["EXAM VENUE"].strip(),
                    defaults={
                        "capacity": int(row["CAPACITY"]),
                        "max_students": int(row["MAX STUDENTS"]),
                        "min_courses": int(row["MIN COURSES"]),
                        "rows": int(row["ROWS"]),
                        "columns": int(row["COLS"]),
                    },
                )
                hall_count += 1
            self.stdout.write(f"  Halls: {hall_count}")

            # 4. Courses (bulk_create with ignore_conflicts is fast)
            existing_codes = set(Course.objects.values_list("code", flat=True))
            to_create: list[Course] = []
            for row in self._read_csv(out / "courses.csv"):
                code = row["COURSE CODE"].strip()
                if code in existing_codes:
                    continue
                to_create.append(
                    Course(
                        code=code,
                        name=row["COURSE TITLE"].strip(),
                        exam_type=row["EXAM TYPE"].strip().upper(),
                    )
                )
            if to_create:
                Course.objects.bulk_create(to_create, batch_size=1000)
            course_by_code = {
                c.code: c for c in Course.objects.only("id", "code")
            }
            self.stdout.write(f"  Courses: {len(course_by_code)}")

            # 5. Classes (per department)
            class_by_dept_name: dict[tuple[str, str], Class] = {}
            classes_dir = out / "classes"
            for dept_dir in sorted(classes_dir.iterdir()):
                if not dept_dir.is_dir():
                    continue
                dept = dept_by_code.get(dept_dir.name.upper())
                if not dept:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  skipping unknown department dir {dept_dir.name}"
                        )
                    )
                    continue
                for row in self._read_csv(dept_dir / "classes.csv"):
                    cls, _ = Class.objects.get_or_create(
                        name=row["Name"].strip(),
                        department=dept,
                        defaults={"size": int(row["Size"])},
                    )
                    if cls.size != int(row["Size"]):
                        cls.size = int(row["Size"])
                        cls.save(update_fields=["size"])
                    class_by_dept_name[(dept.slug, cls.name)] = cls
            self.stdout.write(f"  Classes: {len(class_by_dept_name)}")

            # 6. Class courses (M2M, bulk)
            through = Class.courses.through
            links_to_create: list = []
            existing_pairs: set[tuple[int, int]] = set(
                through.objects.values_list("class_id", "course_id")
            )
            cc_root = out / "class course"
            for dept_dir in sorted(cc_root.iterdir()):
                if not dept_dir.is_dir():
                    continue
                for cls_csv in sorted(dept_dir.glob("*.csv")):
                    cls = class_by_dept_name.get(
                        (dept_dir.name.upper(), cls_csv.stem)
                    )
                    if not cls:
                        continue
                    for row in self._read_csv(cls_csv):
                        course = course_by_code.get(row["COURSE CODE"].strip())
                        if not course:
                            continue
                        pair = (cls.id, course.id)
                        if pair in existing_pairs:
                            continue
                        links_to_create.append(
                            through(class_id=cls.id, course_id=course.id)
                        )
                        existing_pairs.add(pair)
            if links_to_create:
                through.objects.bulk_create(
                    links_to_create, batch_size=2000, ignore_conflicts=True
                )
            self.stdout.write(f"  Class-course links: {len(links_to_create)} new")

            # 7. Students (bulk_create, batched)
            student_root = out / "students"
            student_batch: list[Student] = []
            total_students = 0
            existing_matrics = set(
                Student.objects.values_list("matric_no", flat=True)
            )
            for dept_dir in sorted(student_root.iterdir()):
                if not dept_dir.is_dir():
                    continue
                dept = dept_by_code.get(dept_dir.name.upper())
                if not dept:
                    continue
                for cls_csv in sorted(dept_dir.glob("*.csv")):
                    cls = class_by_dept_name.get(
                        (dept_dir.name.upper(), cls_csv.stem)
                    )
                    if not cls:
                        continue
                    for row in self._read_csv(cls_csv):
                        matric = row["MATRIC NUMBER"].strip()
                        if matric in existing_matrics:
                            continue
                        existing_matrics.add(matric)
                        student_batch.append(
                            Student(
                                matric_no=matric,
                                first_name=row["FIRSTNAME"].strip(),
                                last_name=row["LASTNAME"].strip(),
                                email=row["EMAIL"].strip(),
                                phone=row["PHONE NUMBER"].strip(),
                                department=dept,
                                level=cls,
                            )
                        )
                        if len(student_batch) >= 2000:
                            Student.objects.bulk_create(
                                student_batch, batch_size=2000
                            )
                            total_students += len(student_batch)
                            student_batch.clear()
            if student_batch:
                Student.objects.bulk_create(student_batch, batch_size=2000)
                total_students += len(student_batch)
            self.stdout.write(f"  Students: {total_students}")

    # ---- helpers ----------------------------------------------------------

    @staticmethod
    def _write_csv(path: Path, header: list[str], rows: Iterable[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=header)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    @staticmethod
    def _read_csv(path: Path) -> Iterable[dict]:
        with path.open("r", encoding="utf-8-sig") as fh:
            yield from csv.DictReader(fh)

    @staticmethod
    def _course_title(dept_name: str, level: int, n: int) -> str:
        topic = TITLE_TOPICS[(level - 1 + n) % len(TITLE_TOPICS)]
        roman = ["I", "II", "III", "IV"][(n - 1) % 4]
        return f"{topic} of {dept_name} {roman}"

    @classmethod
    def _build_halls(cls, count: int) -> list[dict]:
        """Mix of auditorium / lecture / classroom halls (1:2:2 ratio)."""
        templates = [
            ("Auditorium", 500, 20, 25, 350, 2),
            ("Auditorium", 500, 20, 25, 350, 2),
            ("Lecture Hall", 300, 15, 20, 200, 2),
            ("Lecture Hall", 300, 15, 20, 200, 2),
            ("Classroom", 150, 10, 15, 100, 1),
        ]
        rows: list[dict] = []
        for i in range(count):
            label, capacity, r, c, max_s, min_c = templates[i % len(templates)]
            rows.append(
                {
                    "EXAM VENUE": f"{label} {i + 1:02d}",
                    "CAPACITY": capacity,
                    "MAX STUDENTS": max_s,
                    "MIN COURSES": min_c,
                    "ROWS": r,
                    "COLS": c,
                }
            )
        return rows

    @classmethod
    def _distribute_class_sizes(
        cls,
        num_departments: int,
        classes_per_dept: int,
        total_students: int,
    ) -> list[int]:
        """
        Generate a list of class sizes summing to roughly `total_students`,
        with each size drawn from a clamped normal-ish distribution.
        """
        total_classes = num_departments * classes_per_dept
        # First pass: random sizes in the configured window
        sizes = [
            random.randint(cls.CLASS_SIZE_MIN, cls.CLASS_SIZE_MAX)
            for _ in range(total_classes)
        ]
        current = sum(sizes)
        if current == total_students:
            return sizes
        # Scale to hit the target while keeping at least 1 student per class
        scale = total_students / current
        scaled = [max(1, int(round(s * scale))) for s in sizes]
        diff = total_students - sum(scaled)
        # Distribute the rounding difference one at a time
        i = 0
        step = 1 if diff > 0 else -1
        while diff != 0:
            idx = i % total_classes
            if step == -1 and scaled[idx] <= 1:
                i += 1
                continue
            scaled[idx] += step
            diff -= step
            i += 1
        return scaled
