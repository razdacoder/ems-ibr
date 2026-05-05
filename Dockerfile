# --- Stage 1: build the React SPA -----------------------------------------
FROM node:20-slim AS frontend
WORKDIR /frontend

# package manifests first for layer-cached installs
COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python runtime ----------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Postgres client for the entrypoint healthcheck; build toolchain for wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-client \
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

# Drop in the React build from stage 1 so collectstatic can pick it up.
COPY --from=frontend /frontend/dist ./frontend/dist

# Materialize STATIC_ROOT inside the image. Failing fast here catches a
# broken build at image-build time, not runtime.
RUN mkdir -p staticfiles media \
    && SECRET_KEY=build-time DEBUG=False python manage.py collectstatic --no-input

RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
