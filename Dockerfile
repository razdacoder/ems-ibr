# Django API (REST + WebSockets). The site and dashboard are a separate
# image built from frontend/Dockerfile.

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Postgres client for the entrypoint healthcheck and the final export of a
# deleted school. pg_dump refuses a server newer than itself, so it comes
# from the PGDG repo at the server's major version; bump PG_MAJOR with it.
# Build toolchain for wheels.
ARG PG_MAJOR=16
RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-common \
    && /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y \
    && apt-get install -y --no-install-recommends \
        postgresql-client-${PG_MAJOR} \
        gcc \
        python3-dev \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps first so the install layer caches across source changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application source. .dockerignore excludes .venv, node_modules,
# db.sqlite3, etc., so this stays lean.
COPY . .

# Materialize STATIC_ROOT inside the image. Failing fast here catches a
# broken build at image-build time, not runtime.
RUN mkdir -p staticfiles media \
    && SECRET_KEY=build-time DEBUG=False python manage.py collectstatic --no-input

RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
