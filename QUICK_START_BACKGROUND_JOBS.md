# Quick Start Guide - Background Jobs

## Development Setup (3 Commands)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Redis (Docker)

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 3. Run Migrations

```bash
python manage.py migrate
```

## Running the System

Open **3 terminal windows** and run:

### Terminal 1: Django Server

```bash
python manage.py runserver
```

### Terminal 2: Celery Worker

```bash
celery -A core worker -l info
```

### Terminal 3: (Optional) Flower Monitoring

```bash
pip install flower
celery -A core flower
# Visit: http://localhost:5555
```

## Quick Commands

### Check Redis

```bash
redis-cli ping  # Should return: PONG
```

### Check Active Tasks

```bash
celery -A core inspect active
```

### View Registered Tasks

```bash
celery -A core inspect registered
```

### Stop All Tasks

```bash
celery -A core purge
```

### Restart Celery Worker

Press `Ctrl+C` in Celery terminal, then run again:

```bash
celery -A core worker -l info
```

## Production Quick Setup

### 1. Environment Variables

```bash
export CELERY_BROKER_URL="redis://your-redis-url:6379/0"
export DATABASE_URL="postgresql://user:pass@host:5432/db"
export SECRET_KEY="your-secret-key"
export DEBUG=False
```

### 2. Start Celery Worker (Systemd)

```bash
sudo systemctl start celery
sudo systemctl enable celery
```

## Troubleshooting

### Celery Not Working?

1. Check Redis: `redis-cli ping`
2. Check worker logs: `celery -A core worker -l debug`
3. Restart worker: `Ctrl+C` and start again

### Tasks Stuck?

```bash
celery -A core purge
```

### Clear Old Jobs

```python
python manage.py shell
>>> from ems.models import BackgroundJob
>>> BackgroundJob.objects.filter(status='success').delete()
```

## What Changed?

### Before (Synchronous)

- User clicks "Generate"
- Browser freezes
- Waits 30-180 seconds
- Might timeout
- Can't use system

### After (Asynchronous)

- User clicks "Generate"
- Sees progress bar immediately
- Can navigate away
- Gets notified when done
- No timeouts!

## Architecture

```
User Browser (HTMX polling every 2s)
    ↓
Django View (creates job, triggers task)
    ↓
Redis (message queue)
    ↓
Celery Worker (processes task)
    ↓
PostgreSQL (updates job progress)
    ↓
HTMX Poll (gets updated progress)
    ↓
User sees progress bar update
```

## Key Files Created/Modified

- ✅ `core/celery.py` - Celery configuration
- ✅ `core/__init__.py` - Celery app initialization
- ✅ `core/settings.py` - Celery settings
- ✅ `ems/models.py` - Added BackgroundJob model
- ✅ `ems/tasks.py` - Async task functions
- ✅ `ems/views.py` - Updated to trigger tasks
- ✅ `ems/urls.py` - Added job status endpoint
- ✅ `templates/dashboard/partials/job-started.html` - Initial UI
- ✅ `templates/dashboard/partials/job-progress.html` - Progress UI
- ✅ `requirements.txt` - Added celery, redis, django-celery-results

## Next Steps

1. **Test locally**: Run all 3 commands and test generation
2. **Set up monitoring**: Install Flower for production
3. **Configure production**: Set up systemd/supervisor
4. **Set up Redis**: Use managed Redis service in production
5. **Monitor jobs**: Check Django admin for BackgroundJob records
