# Ordo production on the VPS

This runbook covers bringing up `deploy/compose.prod.yml` (spec 0003 slice 12), deploying, and the backup and restore drill (spec 0004). Each step is a recommendation. Adjust to your setup.

## What runs

| Service | What it does |
|---|---|
| `traefik` | The only thing with open ports (80, 443). Port 80 redirects to 443. One wildcard certificate for `ordo.app` and `*.ordo.app` through Cloudflare DNS. Routes `/api`, `/ws`, `/media` to `api`, everything else to `dashboard` (`traefik/dynamic.yml`). |
| `postgres` | Postgres 16 with `max_locks_per_transaction=256`, data on the `pgdata` volume. |
| `redis` | Celery broker and Channels layer. |
| `migrate` | One shot. Shared migrations, then every live school, under a lock. Everything below waits for it to exit 0. |
| `api` | Django on Daphne (REST and WebSockets). |
| `worker`, `beat` | Celery. |
| `backup` | Whole database backup to R2 when it starts, then daily at `BACKUP_TIME_UTC`. |
| `dashboard` | The school dashboard and platform console. |

## First boot (fresh database, no schools)

1. **Cloudflare DNS** for `ordo.app`, both **DNS only** (grey cloud): `A @` to the VPS IP, and `A *` to the VPS IP. Create an API token scoped to Zone, DNS, Edit on `ordo.app` only.
2. **R2**: create two private buckets, `ordo-exports` and `ordo-backups`, and an access key. A key scoped to `ordo-backups` alone is better (set `BACKUP_S3_*`).
3. **Secrets** on the VPS, from the repo root:
   ```sh
   cp deploy/.env.example deploy/.env            # Traefik and Postgres
   cp deploy/.env.prod.example deploy/.env.prod  # Django services
   chmod 600 deploy/.env deploy/.env.prod
   ```
   Fill both. The password in `DATABASE_URL` must match `POSTGRES_PASSWORD`.
4. **Start it**:
   ```sh
   docker compose -f deploy/compose.prod.yml up -d --build
   docker compose -f deploy/compose.prod.yml ps        # all healthy, migrate exited 0
   ```
5. **Check the certificate** (AC-10). It should list `*.ordo.app`:
   ```sh
   openssl s_client -connect x.ordo.app:443 -servername x.ordo.app </dev/null 2>/dev/null \
     | openssl x509 -noout -subject -ext subjectAltName
   ```
6. **First Owner**:
   ```sh
   docker compose -f deploy/compose.prod.yml run --rm api \
     python manage.py create_platform_admin --email you@ordo.app --name "Your Name"
   ```
   Then sign in at `https://admin.ordo.app` and enrol your authenticator.
7. **Run the restore drill below before you onboard the first school.** It's the launch blocker.

## Deploying a new release

```sh
git pull
# A backup from before the migrations, in case a release goes wrong.
docker compose -f deploy/compose.prod.yml run --rm backup python manage.py backup_database
docker compose -f deploy/compose.prod.yml up -d --build
```

If `migrate` fails, `api`, `worker`, `beat` and `backup` stay on the previous release. Read `docker compose -f deploy/compose.prod.yml logs migrate`, fix forward, and deploy again.

## Backups

- Every day at `BACKUP_TIME_UTC` (default 01:00), and each time the `backup` container starts, one `pg_dump` of the whole database (public schema plus every school) goes to `BACKUP_BUCKET` at `db/daily/ordo-<UTC time>.dump`. Sundays are also kept under `db/weekly/`.
- A backup counts only once the bucket shows the object at the full size. Only then are old ones pruned (14 daily, 8 weekly by default).
- `docker compose -f deploy/compose.prod.yml ps` shows `backup` as **unhealthy** when the last good backup is more than 26 hours old. See why with `docker compose -f deploy/compose.prod.yml logs backup`.
- To back up right now: `docker compose -f deploy/compose.prod.yml exec backup python manage.py backup_database`.

## Restore drill

You run this once before launch, and ideally every quarter after that. It restores the newest backup into a scratch database next to the live one and compares the two. It never touches the live database (the command refuses `DATABASE_URL` without `--into-live`).

```sh
C="docker compose -f deploy/compose.prod.yml"

# 1. Take a fresh backup and note the key it prints.
$C exec backup python manage.py backup_database

# 2. An empty scratch database.
$C exec postgres createdb -U ordo ordo_restore_drill

# 3. Restore into it (use your real password in the URL).
$C exec backup python manage.py restore_database db/daily/ordo-<time>.dump \
  --target-url postgres://ordo:<password>@postgres:5432/ordo_restore_drill

# 4. Compare schemas and school rows. Both lines should match.
for db in ordo ordo_restore_drill; do
  $C exec postgres psql -U ordo -d $db -Atc \
    "select string_agg(nspname, ',' order by nspname) from pg_namespace where nspname = 'public' or nspname like 'school_%';
     select count(*) from tenancy_school;"
done

# 5. Clean up.
$C exec postgres dropdb -U ordo ordo_restore_drill
```

Record each drill here:

| Date | Backup key | Schemas and schools match | Who |
|---|---|---|---|
| | | | |

## Disaster recovery (new server)

Bring up only Postgres, restore the newest backup into the empty `ordo` database, then start the rest:

```sh
C="docker compose -f deploy/compose.prod.yml"
$C up -d postgres
$C run --rm --no-deps backup sh -c \
  'python manage.py restore_database db/daily/ordo-<time>.dump --target-url "$DATABASE_URL" --into-live'
$C up -d --build
```
