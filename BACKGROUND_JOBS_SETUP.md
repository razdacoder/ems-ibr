# Background Job System Setup

This document explains how to set up and run the background job system for timetable, distribution, and seat allocation generation.

## Prerequisites

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:

- `celery==5.3.6` - Task queue framework
- `redis==5.0.1` - Message broker
- `django-celery-results==2.5.1` - Store task results in Django database

### 2. Set Up Redis

Redis is required as the message broker for Celery.

#### Option A: Using Docker (Recommended for Development)

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

#### Option B: Install Redis Locally

**Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**macOS:**

```bash
brew install redis
brew services start redis
```

**Windows:**
Download from https://github.com/microsoftarchive/redis/releases

#### Option C: Use a Cloud Redis Service

For production, consider using:

- AWS ElastiCache
- Redis Cloud
- Heroku Redis
- DigitalOcean Managed Redis

Set the `CELERY_BROKER_URL` environment variable:

```bash
export CELERY_BROKER_URL="redis://your-redis-host:6379/0"
```

### 3. Run Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

This creates the `BackgroundJob` model table and `django_celery_results` tables.

## Running the System

You need to run **three** separate processes:

### 1. Django Development Server

```bash
python manage.py runserver
```

### 2. Celery Worker

In a **new terminal window**, run:

```bash
celery -A core worker -l info
```

**Options:**

- `-l info`: Set log level (debug, info, warning, error, critical)
- `--concurrency=4`: Number of worker processes (default: CPU count)
- `--pool=solo`: Use solo pool for Windows compatibility

**Windows Users:**

```bash
celery -A core worker -l info --pool=solo
```

### 3. (Optional) Celery Flower - Monitoring UI

For monitoring tasks in real-time:

```bash
pip install flower
celery -A core flower
```

Then visit: http://localhost:5555

## How It Works

### 1. User Triggers Generation

When a user clicks "Generate Timetable", "Generate Distribution", or "Generate Allocation":

1. Django validates the input
2. Creates a `BackgroundJob` record in the database
3. Triggers a Celery task with a unique job ID
4. Returns a template with HTMX polling

### 2. Background Processing

1. Celery worker picks up the task from Redis
2. Task updates job progress in the database
3. Task performs the generation (timetable/distribution/allocation)
4. Task marks job as complete or failed

### 3. UI Updates

1. HTMX polls `/check-job-status/<job_id>/` every 2 seconds
2. Server returns updated progress HTML
3. Progress bar updates automatically
4. When complete, page redirects automatically

## Production Deployment

### Using Systemd (Linux)

Create `/etc/systemd/system/celery.service`:

```ini
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/ems-ibr
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/celery -A core worker -l info --pidfile=/var/run/celery/celery.pid --logfile=/var/log/celery/celery.log
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable celery
sudo systemctl start celery
sudo systemctl status celery
```

### Using Supervisor

Install supervisor:

```bash
sudo apt-get install supervisor
```

Create `/etc/supervisor/conf.d/celery.conf`:

```ini
[program:celery]
command=/path/to/venv/bin/celery -A core worker -l info
directory=/path/to/ems-ibr
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
priority=998
```

Update and start:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start celery
```

### Environment Variables

Set these in production:

```bash
# Django Settings
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis/Celery
CELERY_BROKER_URL=redis://localhost:6379/0
```

## Monitoring and Maintenance

### Check Celery Worker Status

```bash
celery -A core inspect active
celery -A core inspect registered
celery -A core inspect stats
```

### View Active Jobs

```bash
celery -A core inspect active
```

### Purge All Tasks

```bash
celery -A core purge
```

### View Job History

Access the Django admin panel and view the `BackgroundJob` model to see:

- Job status
- Progress
- Error messages
- Completion times

### Clean Up Old Jobs

You can create a management command or cron job to delete old completed jobs:

```python
# In Django shell or management command
from ems.models import BackgroundJob
from datetime import timedelta
from django.utils import timezone

# Delete jobs older than 7 days
cutoff = timezone.now() - timedelta(days=7)
BackgroundJob.objects.filter(completed_at__lt=cutoff).delete()
```

## Troubleshooting

### Celery Worker Not Starting

1. Check Redis is running:

   ```bash
   redis-cli ping
   # Should return: PONG
   ```

2. Check CELERY_BROKER_URL in settings
3. Check for port conflicts (default: 6379)

### Tasks Not Executing

1. Check worker logs:

   ```bash
   celery -A core worker -l debug
   ```

2. Verify tasks are registered:

   ```bash
   celery -A core inspect registered
   ```

3. Check for errors in Django logs

### Progress Not Updating

1. Check HTMX is loaded in base template
2. Check browser console for JavaScript errors
3. Verify `/check-job-status/<job_id>/` endpoint is accessible
4. Check BackgroundJob is being updated in database

### Redis Connection Errors

1. Check Redis is running: `redis-cli ping`
2. Check firewall rules
3. Verify CELERY_BROKER_URL format
4. Check Redis max clients: `redis-cli info clients`

## Performance Optimization

### Concurrency Settings

Adjust worker concurrency based on your server:

```bash
# For CPU-intensive tasks
celery -A core worker --concurrency=4

# For I/O-intensive tasks
celery -A core worker --concurrency=10
```

### Task Time Limits

Already configured in `settings.py`:

```python
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
```

### Redis Connection Pooling

Configure in `settings.py`:

```python
CELERY_BROKER_POOL_LIMIT = 10
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
```

## Security Considerations

1. **Redis Authentication**: Set a password in production

   ```python
   CELERY_BROKER_URL = "redis://:password@localhost:6379/0"
   ```

2. **Network Isolation**: Run Redis on localhost or private network
3. **Task Permissions**: Verify user authentication in views
4. **Rate Limiting**: Consider implementing task rate limits

## Alternative: Django-Q (Redis-Free Option)

If you prefer not to use Redis, you can switch to Django-Q:

1. Replace in `requirements.txt`:

   ```
   django-q==1.3.9
   ```

2. Update `INSTALLED_APPS` in `settings.py`:

   ```python
   INSTALLED_APPS = [
       # ...
       'django_q',
   ]
   ```

3. Configure in `settings.py`:

   ```python
   Q_CLUSTER = {
       'name': 'ems',
       'workers': 4,
       'timeout': 1800,
       'retry': 1800,
       'queue_limit': 50,
       'bulk': 10,
       'orm': 'default',
   }
   ```

4. Update tasks to use `@django_q.task` decorator
5. Run with: `python manage.py qcluster`

**Note**: Django-Q is simpler but less feature-rich than Celery.

## Summary

Your background job system is now set up! Users can:

- Generate timetables without UI blocking
- See real-time progress updates
- Continue using other parts of the system during generation
- Get notified automatically when jobs complete

For production, ensure you:

- Set up Redis properly
- Configure Celery workers with systemd/supervisor
- Set appropriate environment variables
- Monitor job execution and logs
