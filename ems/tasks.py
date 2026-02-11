from celery import shared_task
from datetime import datetime, timedelta
from django.utils import timezone
import random
import string
from .models import User
from .models import (
    BackgroundJob, Class, Course, Distribution, Hall, TimeTable,
    SeatArrangement, DistributionItem, Student, Department
)
from .utils import (
    get_courses, get_halls, split_course, generate,
    distribute_classes_to_halls, save_to_db, print_seating_arrangement
)


def generate_random_students(num_students=100):
    """
    Generate random students if database is empty.
    Creates departments, classes, and students.
    """
    # Check if students already exist
    if Student.objects.exists():
        return
    
    # Get or create departments
    departments = list(Department.objects.all())
    if not departments:
        dept_names = [
            ("Computer Science", "CSC"),
            ("Mathematics", "MAT"),
            ("Physics", "PHY"),
            ("Chemistry", "CHM"),
            ("Biology", "BIO")
        ]
        departments = [
            Department.objects.create(name=name, slug=slug)
            for name, slug in dept_names
        ]
    
    # Get or create classes
    classes = list(Class.objects.all())
    if not classes:
        for dept in departments:
            for level in [100, 200, 300, 400]:
                classes.append(
                    Class.objects.create(
                        name=f"{level} Level",
                        department=dept,
                        size=random.randint(50, 150)
                    )
                )
    
    # Generate random students
    first_names = ["John", "Jane", "Mike", "Sarah", "David", "Emma", "James", "Olivia", "Robert", "Sophia"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    
    students_created = 0
    for i in range(num_students):
        # Generate unique matric number
        year = random.randint(20, 24)
        matric_no = f"{year}{random.randint(1000, 9999)}{random.randint(100, 999)}"
        
        # Check if matric_no already exists
        while Student.objects.filter(matric_no=matric_no).exists():
            matric_no = f"{year}{random.randint(1000, 9999)}{random.randint(100, 999)}"
        
        class_obj = random.choice(classes)
        
        Student.objects.create(
            first_name=random.choice(first_names),
            last_name=random.choice(last_names),
            matric_no=matric_no,
            email=f"student{i}@example.com",
            department=class_obj.department,
            level=class_obj,
            phone=f"080{random.randint(10000000, 99999999)}"
        )
        students_created += 1
    
    return students_created


@shared_task(bind=True)
def generate_timetable_task(self, job_id, user_id, start_date_str, end_date_str):
    """
    Celery task for timetable generation
    """
    job = BackgroundJob.objects.get(job_id=job_id)
    
    try:
        job.status = 'running'
        job.save()
        
        print(f"\n[TASK] Starting timetable generation task {job_id}")
        print(f"[TASK] Date range: {start_date_str} to {end_date_str}")
        print(f"[TASK] Requested by user: {user_id}")
        
        # Parse dates
        startDate = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        endDate = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        # Generate weekday dates (exclude Sundays)
        dates = []
        currentDate = startDate
        while currentDate <= endDate:
            if currentDate.weekday() != 6:  # Exclude Sundays
                dates.append(currentDate)
            currentDate = currentDate + timedelta(days=1)
        
        print(f"[TASK] Generated {len(dates)} valid dates (excluding Sundays)")
        
        total_steps = len(dates) * 2  # Rough estimate
        job.total_steps = total_steps
        job.save()
        
        # Update progress: 10%
        job.progress = int(total_steps * 0.1)
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Loading courses and halls...'})
        
        # Get courses and halls
        courses = get_courses()
        halls = get_halls()
        
        print(f"[TASK] Loaded {len(courses)} courses and {len(halls)} halls")
        
        # Update progress: 20%
        job.progress = int(total_steps * 0.2)
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 20, 'status': 'Splitting courses...'})
        
        # Split courses into AM and PM periods
        AM_courses, PM_courses = split_course(courses)
        
        print(f"[TASK] Split courses - AM: {len(AM_courses)}, PM: {len(PM_courses)}")
        
        # Update progress: 30%
        job.progress = int(total_steps * 0.3)
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 30, 'status': 'Generating timetable...'})
        
        # Generate timetable with incremental progress
        total_dates = len(dates)
        for idx, date in enumerate(dates):
            # Process one date at a time for granular progress
            progress_start = 30 + int((idx / total_dates) * 60)  # 30-90%
            job.progress = int(total_steps * progress_start / 100)
            job.save()
            self.update_state(
                state='PROGRESS',
                meta={'progress': progress_start, 'status': f'Generating timetable for date {idx+1}/{total_dates}...'}
            )
        
        # Actually generate (the utils function handles the DB writes)
        # Delete existing timetables first
        TimeTable.objects.all().delete()
        print(f"[TASK] Deleted existing timetables, starting generation...")
        
        # Capture the summary returned by generate()
        summary = generate(dates, AM_courses, PM_courses, halls)
        
        print(f"[TASK] Timetable generation completed")
        print(f"[TASK] Summary: {summary}")
        
        # Update progress: 90%
        job.progress = int(total_steps * 0.9)
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 90, 'status': 'Finalizing...'})
        
        # Mark as generated in settings
        from .models import SystemSettings
        settings = SystemSettings.objects.first()
        if settings:
            settings.has_timetable = True
            settings.save()
        
        # Complete job
        job.status = 'success'
        job.progress = total_steps
        job.completed_at = timezone.now()
        
        # Include detailed summary in result
        job.result_data = {
            'message': 'Timetable generated successfully',
            'dates_count': len(dates),
            'total_scheduled': summary.get('total_scheduled', 0),
            'am_scheduled': summary.get('am_scheduled', 0),
            'pm_scheduled': summary.get('pm_scheduled', 0),
            'am_skipped': summary.get('am_skipped', 0),
            'pm_skipped': summary.get('pm_skipped', 0),
            'skipped_courses': {
                'AM': summary.get('skipped_am_codes', []),
                'PM': summary.get('skipped_pm_codes', []),
            },
            'timetables_created': TimeTable.objects.count(),
        }
        job.save()
        
        print(f"[TASK] Job completed successfully. Job ID: {job_id}")
        return job.result_data
        
    except Exception as e:
        import traceback
        print(f"[ERROR] Timetable generation failed: {str(e)}")
        print(f"[ERROR] Traceback:\\n{traceback.format_exc()}")
        job.status = 'failed'
        job.error_message = str(e)
        # Store full traceback for debugging
        job.result_data = {
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc()
        }
        job.completed_at = timezone.now()
        job.save()
        raise


@shared_task(bind=True)
def generate_distribution_task(self, job_id, user_id, date, period):
    """
    Celery task for distribution generation
    """
    job = BackgroundJob.objects.get(job_id=job_id)
    
    try:
        job.status = 'running'
        job.total_steps = 100
        job.save()
        
        # Update progress: 10%
        job.progress = 10
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Loading halls and timetables...'})
        
        # Load data
        halls = Hall.objects.all()
        timetables = TimeTable.objects.filter(date=date, period=period).select_related(
            'course', 'class_obj', 'class_obj__department'
        )
        
        if not timetables.exists():
            raise ValueError(f"No timetables found for {date} {period}")
        
        # Update progress: 30%
        job.progress = 30
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 30, 'status': 'Converting halls...'})
        
        # Convert halls (pass the entire queryset, not individual halls)
        from .utils import convert_hall_to_dict
        halls_list = convert_hall_to_dict(halls)
        
        # Update progress: 50%
        job.progress = 50
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 50, 'status': 'Distributing classes to halls...'})
        
        # Distribute classes
        result = distribute_classes_to_halls(list(timetables), halls_list)
        
        # Update progress: 60%
        job.progress = 60
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 60, 'status': 'Classes distributed, preparing to save...'})
        
        # Update progress: 70%
        job.progress = 70
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 70, 'status': 'Saving distribution...'})
        
        # Save to database
        save_to_db(result, date, period)
        
        # Complete job
        job.status = 'success'
        job.progress = 100
        job.completed_at = timezone.now()
        distributions_count = Distribution.objects.filter(date=date, period=period).count()
        job.result_data = {
            'message': 'Distribution generated successfully',
            'distributions_created': distributions_count,
            'date': date,
            'period': period
        }
        job.save()
        
        return {'status': 'success', 'message': 'Distribution generated successfully'}
        
    except Exception as e:
        import traceback
        job.status = 'failed'
        job.error_message = str(e)
        # Store full traceback for debugging
        job.result_data = {
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc()
        }
        job.completed_at = timezone.now()
        job.save()
        raise


@shared_task(bind=True)
def generate_allocation_task(self, job_id, user_id, date, period):
    """
    Celery task for seat allocation generation
    """
    job = BackgroundJob.objects.get(job_id=job_id)
    
    try:
        job.status = 'running'
        job.save()
        
        # Check if students exist, if not generate random ones
        if not Student.objects.exists():
            self.update_state(state='PROGRESS', meta={'progress': 2, 'status': 'No students found, generating random students...'})
            num_generated = generate_random_students(num_students=200)
            self.update_state(state='PROGRESS', meta={'progress': 5, 'status': f'Generated {num_generated} random students. Loading distributions...'})
        
        # Update progress: 5%
        job.progress = 5
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 5, 'status': 'Loading distributions...'})
        
        # Get distributions for the date and period
        distributions = Distribution.objects.filter(
            date=date, period=period
        ).select_related('hall').prefetch_related('items__schedule__course', 'items__schedule__class_obj')
        
        if not distributions.exists():
            raise ValueError(f"No distributions found for {date} {period}. Please generate distribution first.")
        
        total_halls = distributions.count()
        job.total_steps = 100  # Use percentage scale
        job.save()
        
        # Track allocated student IDs globally across all halls
        allocated_ids_by_class = {}
        
        processed_halls = 0
        total_allocated = 0
        total_unplaced = 0
        
        for distribution in distributions:
            processed_halls += 1
            # Progress from 5% to 85% during hall processing
            base_progress = 5 + int((processed_halls - 1) / total_halls * 80)
            
            # Debug logging
            print(f"Processing hall {processed_halls}/{total_halls}: {distribution.hall.name}")
            print(f"Progress: {base_progress}%")
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'progress': base_progress,
                    'status': f'Processing hall {processed_halls}/{total_halls}: {distribution.hall.name}'
                }
            )
            job.progress = base_progress
            job.save()
            
            rows = distribution.hall.rows
            cols = distribution.hall.columns
            hall_capacity = rows * cols
            students = []
            
            # Track student IDs used in this specific hall
            hall_used_ids_by_class = {}
            
            # Build student list for this hall
            for item in distribution.items.all():
                course_code = item.schedule.course.code
                class_obj = item.schedule.class_obj
                class_key = f"{class_obj.id}_{course_code}"
                
                # Initialize tracking sets if needed
                if class_key not in allocated_ids_by_class:
                    allocated_ids_by_class[class_key] = set()
                if class_key not in hall_used_ids_by_class:
                    hall_used_ids_by_class[class_key] = set()
                
                # Get IDs to exclude (already allocated in previous halls or current hall)
                exclude_ids = list(allocated_ids_by_class[class_key] | hall_used_ids_by_class[class_key])
                
                # Get real students, excluding already allocated ones
                real_qs = Student.objects.filter(
                    level=class_obj,
                    department=class_obj.department
                ).exclude(id__in=exclude_ids).order_by('matric_no')
                real_students = list(real_qs[:item.no_of_students])
                
                # Fill remaining with placeholders if needed
                for i, student in enumerate(real_students):
                    students.append({
                        "student_id": student.id,
                        "name": student.matric_no,
                        "course": course_code,
                        "cls_id": class_obj.id
                    })
                    hall_used_ids_by_class[class_key].add(student.id)
                    allocated_ids_by_class[class_key].add(student.id)
            
            # Update progress: student list built
            mid_progress = 5 + int((processed_halls - 0.5) / total_halls * 80)
            self.update_state(
                state='PROGRESS',
                meta={
                    'progress': mid_progress,
                    'status': f'Allocating {len(students)} students in {distribution.hall.name}...'
                }
            )
            job.progress = mid_progress
            job.save()
            
            # Check capacity
            if len(students) > hall_capacity:
                raise ValueError(
                    f"Cannot allocate {len(students)} students to {distribution.hall.name} (capacity: {hall_capacity})"
                )
            
            # Skip if no students to allocate
            if len(students) == 0:
                continue
            
            # Perform seat allocation
            print_seating_arrangement(
                students, rows, cols,
                datetime.strptime(date, "%Y-%m-%d").date(),
                period, distribution.hall.id
            )
            
            # Count results for this hall
            hall_allocated = SeatArrangement.objects.filter(
                date=date, period=period, hall=distribution.hall,
                seat_number__isnull=False
            ).count()
            hall_unplaced = SeatArrangement.objects.filter(
                date=date, period=period, hall=distribution.hall,
                seat_number__isnull=True
            ).count()
            
            total_allocated += hall_allocated
            total_unplaced += hall_unplaced
        
        # Update progress: 90% - all halls processed
        job.progress = 90
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 90, 'status': 'Finalizing allocation...'})
        
        # Complete job
        job.status = 'success'
        job.progress = 100
        job.completed_at = timezone.now()
        job.result_data = {
            'message': 'Seat allocation completed successfully',
            'total_allocated': total_allocated,
            'total_unplaced': total_unplaced,
            'halls_processed': processed_halls,
            'date': date,
            'period': period
        }
        job.save()
        
        return {
            'status': 'success',
            'message': f'Allocated {total_allocated} students across {processed_halls} halls. {total_unplaced} unplaced.'
        }
        
    except Exception as e:
        import traceback
        job.status = 'failed'
        job.error_message = str(e)
        # Store full traceback for debugging
        job.result_data = {
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc()
        }
        job.completed_at = timezone.now()
        job.save()
        raise
