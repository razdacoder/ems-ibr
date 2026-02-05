# EMS-IBR (Examination Management System)

A comprehensive Django-based web application designed to automate and streamline the examination management process for educational institutions. The system handles timetable generation, hall distribution, seat allocation, and attendance sheet creation.

## Features

- **Automated Timetable Generation** - Creates examination schedules based on courses, classes, and available time slots
- **Hall Distribution** - Intelligently distributes classes across available examination halls
- **Seat Allocation** - Automatically assigns seats to students with visual hall layouts
- **Multi-format Exports** - Generate CSV, Excel, and Word document reports
- **User Role Management** - Different access levels for administrators and department users
- **Bulk Data Import** - Upload student, course, and hall data via CSV/Excel files
- **Real-time Dashboard** - Monitor system statistics and examination progress
- **Background Job Processing** - Async task processing with Celery for long-running operations

## Technology Stack

- **Backend**: Django 5.0.3 (Python)
- **Frontend**: HTML5, CSS3, JavaScript, HTMX
- **Database**: SQLite (development) / PostgreSQL (production)
- **Task Queue**: Celery + Redis
- **Document Generation**: python-docx, openpyxl, pandas

## Quick Start (Development)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd ems-ibr

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Superuser credentials (optional)
DJANGO_SUPERUSER_EMAIL_1=admin@example.com
DJANGO_SUPERUSER_PASSWORD_1=admin123
DJANGO_SUPERUSER_FIRSTNAME_1=Admin
DJANGO_SUPERUSER_LASTNAME_1=User
```

### 3. Database Setup

```bash
python manage.py migrate
python manage.py create_superuser  # Creates default admin users
```

### 4. Run Development Server

```bash
python manage.py runserver
```

Access the application at `http://localhost:8000`

## Background Jobs Setup

The system uses Celery for asynchronous task processing (timetable generation, seat allocation, etc.).

### Start Redis (required for Celery)

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### Run Celery Worker

Open a separate terminal:

```bash
celery -A core worker -l info
```

### Optional: Flower Monitoring

```bash
pip install flower
celery -A core flower
# Visit: http://localhost:5555
```

## Docker Deployment

### Build and Run

```bash
# Build the image
docker build -t ems-ibr:latest .

# Run with docker-compose or manually
docker run -p 8000:8000 \
  -e SERVICE_TYPE=web \
  -e SECRET_KEY=your-secret-key \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e REDIS_URL=redis://host:6379 \
  ems-ibr:latest
```

### Push to Registry

```bash
# Docker Hub
docker login
docker build -t yourusername/ems-ibr:latest .
docker push yourusername/ems-ibr:latest

# GitHub Container Registry
echo "YOUR_TOKEN" | docker login ghcr.io -u YOUR_USERNAME --password-stdin
docker build -t ghcr.io/yourusername/ems-ibr:latest .
docker push ghcr.io/yourusername/ems-ibr:latest
```

## Railway Deployment

### Services Required

1. **PostgreSQL** - Database
2. **Redis** - Message broker for Celery
3. **Web Service** - Django application
4. **Worker Service** - Celery worker

### Environment Variables

**Web Service:**
```env
SERVICE_TYPE=web
SECRET_KEY=<your-secret-key>
DEBUG=False
ALLOWED_HOSTS=your-app.railway.app
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

**Worker Service:**
```env
SERVICE_TYPE=worker
SECRET_KEY=<same-as-web>
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

## Project Structure

```
ems-ibr/
├── core/                 # Project settings & Celery config
│   ├── settings.py
│   ├── celery.py
│   └── urls.py
├── ems/                  # Main application
│   ├── models.py        # Data models
│   ├── views.py         # Business logic
│   ├── tasks.py         # Celery async tasks
│   ├── urls.py          # URL routing
│   ├── utils.py         # Utility functions
│   ├── csv_gen.py       # Export functionality
│   └── broadsheet.py    # Excel report generation
├── templates/           # HTML templates
├── static/              # CSS, JS, images
├── Dockerfile           # Container configuration
├── docker-entrypoint.sh # Container startup script
└── requirements.txt     # Python dependencies
```

## Data Models

- **User** - Custom user model with email authentication
- **Department** - Academic departments
- **Course** - Courses with exam types (PBE/CBE)
- **Class** - Student groups within departments
- **Student** - Individual student records
- **Hall** - Examination venues with capacity and layout
- **TimeTable** - Examination schedules
- **Distribution** - Hall allocation for examinations
- **SeatArrangement** - Individual seat assignments
- **BackgroundJob** - Async task tracking

## Data Upload Sequence

Follow this sequence for proper data setup:

1. **Admin uploads courses** (via Dashboard > Courses)
2. **Upload departments** (via Dashboard > Departments)
3. **Upload classes** (via Dashboard > Classes)
4. **Upload halls** (via Dashboard > Halls)
5. **Link courses to classes** (via Dashboard > Classes > Courses)
6. **Upload students** (optional, for seat allocation)
7. **Generate timetable**

## User Roles

- **Super Administrator** - Full system access
- **Staff/Administrator** - Can manage all data and generate reports
- **Department User** - Limited access to department-specific data

## Reports & Exports

- **Timetable CSV** - Department-specific schedules
- **Broadsheet Excel** - Comprehensive formatted timetable
- **Distribution CSV** - Hall-to-class assignments
- **Seating Arrangements** - ZIP file with per-course CSVs
- **Attendance Sheets** - Word documents per hall/course

## Useful Commands

```bash
# Database
python manage.py migrate                    # Apply migrations
python manage.py dumpdata > backup.json    # Backup database
python manage.py loaddata backup.json      # Restore database

# Celery
celery -A core worker -l info              # Start worker
celery -A core inspect active              # Check active tasks
celery -A core purge                       # Clear task queue

# Static files
python manage.py collectstatic --noinput   # Collect static files
```

## Troubleshooting

### Celery Not Working?
1. Check Redis: `redis-cli ping` (should return PONG)
2. Check worker logs: `celery -A core worker -l debug`
3. Restart worker and try again

### Tasks Stuck?
```bash
celery -A core purge  # Clear all pending tasks
```

### Generate SECRET_KEY
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

## License

MIT License

## Author

Developed for educational institution examination management.
