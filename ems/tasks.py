from celery import shared_task
from datetime import datetime, timedelta
from django.utils import timezone
from .models import User
from .models import (
    BackgroundJob, Class, Course, Distribution, Hall, TimeTable,
    SeatArrangement, DistributionItem, Student
)
from .utils import (
    get_courses, get_halls, split_course, generate,
    distribute_classes_to_halls, save_to_db, print_seating_arrangement
)



@shared_task(bind=True)
def generate_timetable_task(self, job_id, user_id, start_date_str, end_date_str):
    """
    Celery task for timetable generation
    """
    job = BackgroundJob.objects.get(job_id=job_id)
    
    try:
        job.status = 'running'
        job.save()
        
        # Parse dates
        startDate = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        endDate = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        # Generate weekday dates (exclude Sundays)
        dates = []
        currentDate = startDate
        while currentDate <= endDate:
            if currentDate.weekday() != 6:  # Exclude Sundays
                dates.append(currentDate)
            currentDate = currentDate + datetime.timedelta(days=1)
        
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
        
        # Update progress: 20%
        job.progress = int(total_steps * 0.2)
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 20, 'status': 'Splitting courses...'})
        
        # Split courses into AM and PM periods
        AM_courses, PM_courses = split_course(courses)
        
        # Update progress: 30%
        job.progress = int(total_steps * 0.3)
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 30, 'status': 'Generating timetable...'})
        
        # Generate timetable
        generate(dates, AM_courses, PM_courses, halls)
        
        # Update progress: 90%
        job.progress = int(total_steps * 0.9)
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 90, 'status': 'Finalizing...'})
        
        # Mark as generated in settings
        from .models import SystemSettings
        settings = SystemSettings.objects.first()
        settings.has_timetable = True
        settings.save()
        
        # Complete job
        job.status = 'success'
        job.progress = total_steps
        job.completed_at = timezone.now()
        job.result_data = {
            'message': 'Timetable generated successfully',
            'dates_count': len(dates),
            'timetables_created': TimeTable.objects.count()
        }
        job.save()
        
        return {'status': 'success', 'message': 'Timetable generated successfully'}
        
    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
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
        
        # Convert halls
        from .utils import convert_hall_to_dict
        halls_list = [convert_hall_to_dict(hall) for hall in halls]
        
        # Update progress: 50%
        job.progress = 50
        job.save()
        self.update_state(state='PROGRESS', meta={'progress': 50, 'status': 'Distributing classes to halls...'})
        
        # Distribute classes
        result = distribute_classes_to_halls(list(timetables), halls_list)
        
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
        job.status = 'failed'
        job.error_message = str(e)
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
        job.total_steps = total_halls * 100
        job.save()
        
        # Track allocated student IDs globally across all halls
        allocated_ids_by_class = {}
        
        processed_halls = 0
        total_allocated = 0
        total_unplaced = 0
        
        for distribution in distributions:
            processed_halls += 1
            base_progress = int((processed_halls - 1) / total_halls * 100)
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'progress': base_progress,
                    'status': f'Processing hall {processed_halls}/{total_halls}: {distribution.hall.name}'
                }
            )
            
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
            
            # Check capacity
            if len(students) > hall_capacity:
                raise ValueError(
                    f"Cannot allocate {len(students)} students to {distribution.hall.name} (capacity: {hall_capacity})"
                )
            
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
            
            # Update job progress
            job.progress = int(processed_halls / total_halls * 90)
            job.save()
        
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
        job.status = 'failed'
        job.error_message = str(e)
        job.completed_at = timezone.now()
        job.save()
        raise
