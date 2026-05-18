#!/bin/bash

set -e

echo "Starting EMS-IBR Service..."
echo "SERVICE_TYPE: ${SERVICE_TYPE:-web}"

# Function to wait for PostgreSQL
wait_for_postgres() {
    echo "Waiting for PostgreSQL to be ready..."
    python << END
import sys
import time
import psycopg2
from urllib.parse import urlparse
import os

max_retries = 30
retry_count = 0

database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("ERROR: DATABASE_URL environment variable is not set")
    sys.exit(1)

# Parse the database URL
result = urlparse(database_url)
username = result.username
password = result.password
database = result.path[1:]
hostname = result.hostname
port = result.port

while retry_count < max_retries:
    try:
        conn = psycopg2.connect(
            dbname=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        conn.close()
        print("PostgreSQL is ready!")
        sys.exit(0)
    except psycopg2.OperationalError as e:
        retry_count += 1
        print(f"PostgreSQL not ready yet (attempt {retry_count}/{max_retries})...")
        time.sleep(2)

print("ERROR: Could not connect to PostgreSQL after maximum retries")
sys.exit(1)
END
}

# Function to wait for Redis
wait_for_redis() {
    echo "Waiting for Redis to be ready..."
    python << END
import sys
import time
import redis
from urllib.parse import urlparse
import os

max_retries = 30
retry_count = 0

redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

while retry_count < max_retries:
    try:
        r = redis.from_url(redis_url)
        r.ping()
        print("Redis is ready!")
        sys.exit(0)
    except (redis.ConnectionError, redis.TimeoutError) as e:
        retry_count += 1
        print(f"Redis not ready yet (attempt {retry_count}/{max_retries})...")
        time.sleep(2)

print("ERROR: Could not connect to Redis after maximum retries")
sys.exit(1)
END
}

# Check SERVICE_TYPE and execute appropriate commands
if [ "${SERVICE_TYPE}" = "worker" ]; then
    echo "Starting Celery Worker..."
    
    # Wait for dependencies
    wait_for_postgres
    wait_for_redis
    
    # Start Celery worker
    exec celery -A core worker -l info --concurrency=4
    
elif [ "${SERVICE_TYPE}" = "beat" ]; then
    echo "Starting Celery Beat..."
    
    # Wait for dependencies
    wait_for_redis
    
    # Start Celery beat
    exec celery -A core beat -l info
    
else
    # Default: web service. Channels needs ASGI, so we run Daphne instead of
    # Gunicorn — Gunicorn-on-WSGI silently drops WebSocket upgrades.
    echo "Starting Web Service..."

    wait_for_postgres

    # Frontend: the image bundles the built React SPA at frontend/dist
    # (Dockerfile stage 1). Django serves frontend/dist/index.html for every
    # non-/api, non-/admin route and WhiteNoise serves its hashed assets from
    # /static/. Fail loudly if the build is absent so it isn't a mystery 500
    # on every page (a missing build still leaves the API usable).
    if [ -f frontend/dist/index.html ]; then
        echo "Frontend SPA build found (frontend/dist/index.html)."
    else
        echo "WARNING: frontend/dist/index.html is missing."
        echo "         The API will run, but every non-/api route will 500"
        echo "         because there is no SPA shell to serve. Rebuild the"
        echo "         image so the Dockerfile frontend stage runs, or run"
        echo "         'npm --prefix frontend run build' before starting."
    fi

    # collectstatic materializes the SPA's hashed assets (and admin/DRF
    # static) into STATIC_ROOT for WhiteNoise. It already ran at image-build
    # time; re-running is a no-op in the typical case but keeps a
    # volume-mounted copy correct.
    echo "Collecting static files (incl. the React SPA bundle)..."
    python manage.py collectstatic --no-input

    echo "Running database migrations..."
    python manage.py migrate --noinput

    echo "Creating superuser if needed..."
    python manage.py create_superuser || true

    echo "Starting Daphne (ASGI) on port ${PORT:-8000}..."
    exec daphne \
        -b 0.0.0.0 \
        -p "${PORT:-8000}" \
        --proxy-headers \
        core.asgi:application
fi
