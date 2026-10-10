#!/usr/bin/env bash
set -o errexit

# Non-Docker build of the Django API (e.g. Render's build command); keep the
# steps here in sync with the Dockerfile. The frontend is a separate Node
# service: `pnpm install --frozen-lockfile && pnpm build` then `pnpm start`,
# in frontend/.

# --- Backend deps ---------------------------------------------------------
pip install -r requirements.txt

# --- Django ---------------------------------------------------------------
python manage.py collectstatic --no-input
python manage.py makemigrations ems
python manage.py migrate ems
python manage.py migrate
python manage.py create_superuser
