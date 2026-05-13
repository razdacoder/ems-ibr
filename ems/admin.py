from django.contrib import admin
from .models import User, Department, Course, Class, TimeTable, Hall, Distribution, DistributionItem, SeatArrangement, Student, SystemSettings, BackgroundJob, Faculty, GenerationConstraints


# Register your models here.


@admin.register(BackgroundJob)
class BackgroundJobAdmin(admin.ModelAdmin):
    list_display = ['job_id', 'job_type', 'status', 'progress_percentage', 'created_by', 'started_at', 'completed_at']
    list_filter = ['status', 'job_type', 'created_by', 'started_at']
    search_fields = ['job_id', 'created_by__email', 'created_by__first_name', 'created_by__last_name']
    readonly_fields = ['job_id', 'started_at', 'completed_at', 'progress_percentage']
    ordering = ['-started_at']
    
    def progress_percentage(self, obj):
        return f"{obj.progress_percentage}%"
    progress_percentage.short_description = "Progress"


admin.site.register(User)
admin.site.register(Faculty)
admin.site.register(Department)
admin.site.register(Course)
admin.site.register(Class)
admin.site.register(TimeTable)
admin.site.register(Hall)
admin.site.register(Distribution)
admin.site.register(DistributionItem)
admin.site.register(SeatArrangement)
admin.site.register(Student)
admin.site.register(SystemSettings)
admin.site.register(GenerationConstraints)
