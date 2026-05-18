#!/usr/bin/env bash
set -o errexit

# Non-Docker build (e.g. Render's build command). The Dockerfile has its own
# two-stage build; keep the steps here in sync with it.

# --- Backend deps ---------------------------------------------------------
pip install -r requirements.txt

# --- Frontend build -------------------------------------------------------
# The React SPA must be built BEFORE collectstatic: Vite emits to
# frontend/dist/, which is a STATICFILES_DIR, and core/urls.py serves
# frontend/dist/index.html as the SPA shell. Without this step the deploy
# ships an API with no UI. Mirrors the Node stage of the Dockerfile and
# requires Node 20+/npm on the build environment.
pushd frontend > /dev/null
if [ -f package-lock.json ]; then
  npm ci
else
  npm install
fi
npm run build
popd > /dev/null

# --- Django ---------------------------------------------------------------
python manage.py collectstatic --no-input
python manage.py makemigrations ems
python manage.py migrate ems
python manage.py migrate
python manage.py create_superuser
