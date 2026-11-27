#!/usr/bin/env bash
set -o errexit

# Non-Docker build of the Django API (e.g. Render's build command); keep the
# steps here in sync with the Dockerfile. The frontend is a separate Node
# service: `pnpm install --frozen-lockfile && pnpm build` then `pnpm start`,
# in frontend/.
#
# No migrations here: they run in the pre-deploy command,
# `python manage.py migrate_platform`, so a failed migration stops the release.

# --- Backend deps ---------------------------------------------------------
pip install -r requirements.txt

# --- Django ---------------------------------------------------------------
python manage.py collectstatic --no-input
