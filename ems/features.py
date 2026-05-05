"""Static feature catalog for the public marketing pages.

This used to be a hardcoded dict inside ``ems.views.feature_detail_view``.
Lifted into its own module so the API view (and the React frontend) can
share a single source of truth.
"""

FEATURES_DATA: dict[str, dict] = {
    "timetable-generation": {
        "title": "Timetable Generation",
        "subtitle": "Automatically create conflict-free exam schedules.",
        "overview": (
            "The timetable generation module is the core of ExamNova. It "
            "automatically builds a comprehensive examination schedule based "
            "on courses, classes, and available time slots. It ensures that no "
            "class has conflicting exams, appropriately handles different exam "
            "types (PBE vs CBE), and intelligently spaces out the schedule."
        ),
        "icon": "calendar-check",
        "capabilities": [
            "AM/PM period scheduling",
            "CBE vs PBE exam type handling (exclusive slots for CBE)",
            "Sunday exclusion & date range validation",
            "Background processing with real-time progress tracking",
            "Department-level and institution-wide views",
            "Export to CSV and comprehensive Excel broadsheet",
        ],
        "how_it_works": [
            "Upload all required data (departments, courses, classes, halls).",
            "Set the start and end dates for the examination period.",
            "Click 'Generate' and monitor the progress.",
            "Review and export the generated timetable.",
        ],
        "benefits": [
            "Saves days of manual scheduling work.",
            "Eliminates human errors and exam conflicts.",
            "Provides a clear, organized schedule for both staff and students.",
        ],
    },
    "hall-distribution": {
        "title": "Hall Distribution",
        "subtitle": "Intelligently distribute class groups across examination halls.",
        "overview": (
            "Once the timetable is set, the Hall Distribution module takes "
            "over. It determines which classes will sit in which halls for "
            "each specific date and period."
        ),
        "icon": "layout-grid",
        "capabilities": [
            "Capacity-aware hall assignment",
            "Large class splitting across multiple halls",
            "Utilization statistics & optimization grade",
            "Distribution CSV export",
            "Per-date, per-period configuration",
        ],
        "how_it_works": [
            "Select a specific date and period from the generated timetable.",
            "Click 'Generate Distribution'.",
            "Review the assigned halls and class groups.",
            "Check the efficiency statistics to ensure optimal usage.",
        ],
        "benefits": [
            "Maximizes space utilization.",
            "Prevents overcrowding in examination halls.",
            "Provides clear metrics on how well resources are being used.",
        ],
    },
    "seat-allocation": {
        "title": "Seat Allocation",
        "subtitle": "Assign specific seats with strict anti-cheating constraints.",
        "overview": (
            "The Seat Allocation module is an advanced seating algorithm "
            "designed to prevent cheating. It assigns specific seat numbers "
            "to individual students, ensuring that no two students taking the "
            "same course are seated next to each other in any direction."
        ),
        "icon": "grid-3x3",
        "capabilities": [
            "8-directional adjacency enforcement",
            "Pattern-based seating (checkerboard, diagonal multi-pass)",
            "Visual seat grid layout per hall",
            "Manual seat assignment for unplaced students",
            "Detailed placed vs unplaced summary",
        ],
        "how_it_works": [
            "After distribution, generate seat allocation for a date and period.",
            "The system processes each hall, applying adjacency constraints.",
            "Review the visual seat grid for each hall.",
            "Manually assign seats to any unplaced students if necessary.",
        ],
        "benefits": [
            "Significantly reduces the potential for cheating.",
            "Provides a clear, organized seating plan for invigilators.",
            "Visual grid makes it easy to understand the hall layout.",
        ],
    },
    "reports-exports": {
        "title": "Reports & Exports",
        "subtitle": "Generate professional documents for exam halls.",
        "overview": (
            "ExamNova provides a comprehensive suite of reporting and export "
            "tools to generate all the necessary documentation for conducting "
            "examinations."
        ),
        "icon": "file-text",
        "capabilities": [
            "DOCX attendance sheets with school branding and signature fields",
            "Excel broadsheet (department & day-period views)",
            "CSV timetable export per department",
            "ZIP packages of seat arrangements per course",
            "Walk-in rows for late registrations",
        ],
        "how_it_works": [],
        "benefits": [
            "Produces ready-to-print, professional documents.",
            "Reduces manual paperwork.",
            "Ensures consistency across all examination records.",
        ],
    },
    "data-management": {
        "title": "Data Management",
        "subtitle": "Complete CRUD and bulk CSV upload support for every entity.",
        "overview": (
            "A robust data management system allows administrators and exam "
            "officers to easily input and manage the foundational data "
            "required for the examination process."
        ),
        "icon": "database",
        "capabilities": [
            "Manual create, edit, delete for all entities",
            "Bulk CSV upload with strict validation",
            "ZIP-based multi-file upload support",
            "Duplicate detection and conflict handling",
            "Upload lock after timetable generation",
        ],
        "how_it_works": [],
        "benefits": [
            "Fast and efficient data entry via bulk uploads.",
            "Maintains data integrity with strict validation rules.",
            "Clear error reporting helps quickly identify data issues.",
        ],
    },
    "background-jobs": {
        "title": "Background Job Monitor",
        "subtitle": "Track, retry, and manage all long-running tasks.",
        "overview": (
            "ExamNova uses asynchronous background processing for heavy tasks "
            "like timetable generation and seat allocation. The Job Monitor "
            "provides full visibility into these processes."
        ),
        "icon": "list-checks",
        "capabilities": [
            "Real-time progress tracking",
            "Filter by status and job type",
            "Retry failed jobs with one click",
            "Detailed error messages and tracebacks",
            "Job history with parameters and result metrics",
        ],
        "how_it_works": [],
        "benefits": [
            "Ensures the system remains responsive during heavy processing.",
            "Provides transparency into the status of complex operations.",
            "Easy recovery from failures via the retry mechanism.",
        ],
    },
}
