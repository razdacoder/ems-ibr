# Railway Deployment Guide - EMS-IBR (Docker Container Registry)

This guide covers deploying the EMS-IBR Django application to Railway using Docker Container Registry with managed PostgreSQL and Redis services.

## Architecture Overview

The deployment consists of **4 Railway services**:

1. **PostgreSQL Database** - Managed by Railway
2. **Redis** - Managed by Railway
3. **Web Application** - Django + Gunicorn (Docker Container from Registry)
4. **Celery Worker** - Background job processor (Docker Container from Registry)

## Prerequisites

- Railway account ([railway.app](https://railway.app))
- Docker installed locally ([docker.com](https://docker.com))
- Docker Hub account (or GitHub account for GHCR)

## Step 1: Create Railway Project

1. Go to [railway.app](https://railway.app) and sign in
2. Click **"New Project"**
3. Select **"Empty Project"**
4. Give it a name (e.g., `ems-ibr-production`)

## Step 2: Add PostgreSQL Service

1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Railway will provision a PostgreSQL database
4. Note: Railway automatically creates a `DATABASE_URL` variable

## Step 3: Add Redis Service

1. Click **"+ New"** again
2. Select **"Database"** → **"Add Redis"**
3. Railway will provision a Redis instance
4. Note: Railway automatically creates a `REDIS_URL` variable

## Step 4: Build and Push Docker Image

### Option A: Docker Hub

1. **Login to Docker Hub**:

```bash
docker login
```

2. **Build the Docker image**:

```bash
# Replace 'yourusername' with your Docker Hub username
docker build -t yourusername/ems-ibr:latest .
```

3. **Test the image locally (optional)**:

```bash
docker run -p 8000:8000 \
  -e SERVICE_TYPE=web \
  -e SECRET_KEY=test-key \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e REDIS_URL=redis://host:6379 \
  yourusername/ems-ibr:latest
```

4. **Push to Docker Hub**:

```bash
docker push yourusername/ems-ibr:latest
```

### Option B: GitHub Container Registry (GHCR)

1. **Create GitHub Personal Access Token**:
   - Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Generate new token with `write:packages` scope
   - Copy the token

2. **Login to GHCR**:

```bash
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

3. **Build the Docker image**:

```bash
# Replace 'yourusername' with your GitHub username
docker build -t ghcr.io/yourusername/ems-ibr:latest .
```

4. **Push to GHCR**:

```bash
docker push ghcr.io/yourusername/ems-ibr:latest
```

### Option C: Automated CI/CD with GitHub Actions

Create `.github/workflows/docker-publish.yml`:

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

## Step 5: Deploy Web Application from Container Registry

1. In your Railway project, click **"+ New"**
2. Select **"Empty Service"**
3. Name it `web` or `django-app`

### Configure Web Service

1. Go to the service **Settings** → **Source**:
   - Select **"Docker Image"**
   - Enter your image: `yourusername/ems-ibr:latest` (Docker Hub)
   - Or: `ghcr.io/yourusername/ems-ibr:latest` (GHCR)

2. If using a private registry, add **Image Pull Credentials**:
   - Username: Your Docker Hub/GitHub username
   - Password: Your Docker Hub password or GitHub token

3. Go to **Variables** tab and add:

```env
# Service Type
SERVICE_TYPE=web

# Django Settings
SECRET_KEY=your-super-secret-key-here-change-this
DEBUG=False
ALLOWED_HOSTS=your-app.railway.app,your-custom-domain.com

# Superuser Configuration (Optional)
DJANGO_SUPERUSER_EMAIL_1=admin@example.com
DJANGO_SUPERUSER_PASSWORD_1=SecurePassword123!
DJANGO_SUPERUSER_FIRSTNAME_1=Admin
DJANGO_SUPERUSER_LASTNAME_1=User

# Database & Redis (Reference Railway services)
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

4. Under **Settings** → **Networking**:
   - Enable **"Generate Domain"** to get a public URL
   - Or add your custom domain

5. Click **"Deploy"** to start the service

## Step 6: Deploy Celery Worker from Container Registry

1. Click **"+ New"** → **"Empty Service"**
2. Name it `celery-worker`

### Configure Celery Worker Service

1. Go to the service **Settings** → **Source**:
   - Select **"Docker Image"**
   - Enter your image: `yourusername/ems-ibr:latest` (same image as web)
   - Or: `ghcr.io/yourusername/ems-ibr:latest`

2. If using a private registry, add **Image Pull Credentials**:
   - Username: Your Docker Hub/GitHub username
   - Password: Your Docker Hub password or GitHub token

3. Go to **Variables** tab and add:

```env
# Service Type (THIS IS CRITICAL!)
SERVICE_TYPE=worker

# Django Settings (same as web)
SECRET_KEY=your-super-secret-key-here-change-this
DEBUG=False

# Database & Redis (Reference the same services)
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

4. Click **"Deploy"** to start the worker

## Step 7: (Optional) Add Celery Beat Service

If you need scheduled/periodic tasks:

1. Click **"+ New"** → **"Empty Service"**
2. Name it `celery-beat`

### Configure Celery Beat Service

1. Go to the service **Settings** → **Source**:
   - Select **"Docker Image"**
   - Enter your image: `yourusername/ems-ibr:latest` (same image)

2. Go to **Variables** tab and add:

```env
SERVICE_TYPE=beat
SECRET_KEY=your-super-secret-key-here-change-this
REDIS_URL=${{Redis.REDIS_URL}}
```

3. Click **"Deploy"** to start the beat scheduler

## Step 8: Update Your Docker Image

When you make changes to your application:

1. **Rebuild the Docker image**:

```bash
docker build -t yourusername/ems-ibr:latest .
```

2. **Push to registry**:

```bash
docker push yourusername/ems-ibr:latest
```

3. **Redeploy Railway services**:
   - Go to each service in Railway
   - Click **"Redeploy"** or wait for auto-redeploy
   - Railway will pull the latest image

### Using Image Tags for Better Version Control

```bash
# Build with version tag
docker build -t yourusername/ems-ibr:v1.0.0 .
docker build -t yourusername/ems-ibr:latest .

# Push both tags
docker push yourusername/ems-ibr:v1.0.0
docker push yourusername/ems-ibr:latest
```

Then in Railway, you can specify: `yourusername/ems-ibr:v1.0.0` for specific versions.

## Environment Variables Reference

### Required for All Services

| Variable       | Description           | Example                      |
| -------------- | --------------------- | ---------------------------- |
| `SECRET_KEY`   | Django secret key     | `django-insecure-xyz...`     |
| `DATABASE_URL` | PostgreSQL connection | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL`    | Redis connection      | `${{Redis.REDIS_URL}}`       |

### Web Service Only

| Variable                       | Description               | Example                       |
| ------------------------------ | ------------------------- | ----------------------------- |
| `SERVICE_TYPE`                 | Service type identifier   | `web`                         |
| `DEBUG`                        | Debug mode (set to False) | `False`                       |
| `ALLOWED_HOSTS`                | Comma-separated hosts     | `app.railway.app,example.com` |
| `DJANGO_SUPERUSER_EMAIL_1`     | Admin email               | `admin@example.com`           |
| `DJANGO_SUPERUSER_PASSWORD_1`  | Admin password            | `SecurePassword123!`          |
| `DJANGO_SUPERUSER_FIRSTNAME_1` | Admin first name          | `Admin`                       |
| `DJANGO_SUPERUSER_LASTNAME_1`  | Admin last name           | `User`                        |

### Worker Service Only

| Variable       | Description             | Example  |
| -------------- | ----------------------- | -------- |
| `SERVICE_TYPE` | Service type identifier | `worker` |

### Beat Service Only (Optional)

| Variable       | Description             | Example |
| -------------- | ----------------------- | ------- |
| `SERVICE_TYPE` | Service type identifier | `beat`  |

## Service Startup Order

Railway services start in parallel, but the `docker-entrypoint.sh` script includes wait logic:

1. **PostgreSQL & Redis** - Start first (managed by Railway)
2. **Web Service** - Waits for PostgreSQL, runs migrations, then starts
3. **Celery Worker** - Waits for PostgreSQL & Redis, then starts
4. **Celery Beat** (optional) - Waits for Redis, then starts

## Accessing Your Application

Once deployed:

1. **Web Interface**: `https://your-app.railway.app`
2. **Admin Panel**: `https://your-app.railway.app/admin`
3. **Login**: Use the superuser credentials you configured

## Monitoring & Logs

### View Logs

1. In Railway dashboard, click on each service
2. Go to **"Deployments"** tab
3. Click on the active deployment
4. View real-time logs

### Key Log Indicators

**Web Service:**

```
✓ PostgreSQL is ready!
✓ Collecting static files...
✓ Running database migrations...
✓ Creating superuser if needed...
✓ Starting Gunicorn on port 8000...
```

**Celery Worker:**

```
✓ PostgreSQL is ready!
✓ Redis is ready!
✓ Starting Celery Worker...
✓ celery@hostname ready.
```

## Database Migrations

Migrations run automatically when the web service starts. To run migrations manually:

```bash
# Using Railway CLI
railway run python manage.py migrate
```

## Troubleshooting

### Issue: Web service crashes immediately

**Solution:** Check that `DATABASE_URL` is correctly referenced:

```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

### Issue: Celery worker not processing tasks

**Solutions:**

1. Verify `SERVICE_TYPE=worker` is set
2. Check `REDIS_URL` is correctly configured
3. View worker logs for connection errors

### Issue: Static files not loading

**Solution:** The app uses WhiteNoise for static files. Ensure:

- `collectstatic` runs successfully (check web service logs)
- `DEBUG=False` in production
- `ALLOWED_HOSTS` includes your domain

### Issue: Migrations not running

**Solution:**

- Check web service logs for migration errors
- Manually run: `railway run python manage.py migrate`
- Ensure `DATABASE_URL` is accessible

### Issue: Superuser not created

**Solution:** Verify all superuser environment variables are set:

```env
DJANGO_SUPERUSER_EMAIL_1=admin@example.com
DJANGO_SUPERUSER_PASSWORD_1=SecurePassword123!
DJANGO_SUPERUSER_FIRSTNAME_1=Admin
DJANGO_SUPERUSER_LASTNAME_1=User
```

## Scaling

### Horizontal Scaling (Web Service)

1. Go to web service **Settings** → **Replicas**
2. Increase replica count (requires paid plan)

### Vertical Scaling

Railway automatically allocates resources based on usage. For high traffic:

1. Upgrade to a paid plan for more resources
2. Adjust Gunicorn workers in [docker-entrypoint.sh](docker-entrypoint.sh):
   ```bash
   --workers 8 \
   --threads 4
   ```

### Celery Worker Scaling

To add more worker instances:

1. Duplicate the worker service
2. Rename it (e.g., `celery-worker-2`)
3. Deploy with same environment variables

## Maintenance

### Update Application

**Using GitHub:**

1. Push changes to your repository
2. Railway auto-deploys on push

**Using Railway CLI:**

```bash
railway up
```

### Database Backup

Railway Pro provides automatic PostgreSQL backups. To manually backup:

```bash
# Export database
railway run pg_dump $DATABASE_URL > backup.sql
```

### View Background Jobs

Navigate to: `https://your-app.railway.app/jobs`

Monitor:

- Timetable generation tasks
- Student distribution tasks
- Seat allocation tasks

## Cost Optimization

1. **Starter Plan**: Free tier with 500 hours/month
2. **Pro Plan**: $5/month + usage-based pricing
3. **Cost Tips**:
   - Use one worker instance initially
   - Enable services only when needed
   - Monitor usage in Railway dashboard

## Security Checklist

- [ ] Set `DEBUG=False` in production
- [ ] Use strong `SECRET_KEY` (generate new one)
- [ ] Configure `ALLOWED_HOSTS` properly
- [ ] Use strong superuser password
- [ ] Enable Railway's security features
- [ ] Regularly update dependencies
- [ ] Monitor logs for suspicious activity

## Additional Resources

- [Railway Documentation](https://docs.railway.app)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)
- [Celery Documentation](https://docs.celeryproject.org)

## Support

For issues specific to:

- **Railway**: Check [Railway Discord](https://discord.gg/railway)
- **Django**: See [Django Forums](https://forum.djangoproject.com)
- **This Project**: Create an issue in the GitHub repository

---

**Happy Deploying! 🚀**
