# Quick Start: Docker Container Registry Deployment

This guide helps you quickly build, push, and deploy the EMS-IBR Docker image to Railway using a container registry.

## 🚀 Quick Deploy (3 Steps)

### Step 1: Build and Push Docker Image

**Option A: Using the automated script**

```bash
# For Docker Hub
./docker-build-push.sh --registry dockerhub --username YOUR_DOCKERHUB_USERNAME --version v1.0.0

# For GitHub Container Registry
./docker-build-push.sh --registry ghcr --username YOUR_GITHUB_USERNAME --version v1.0.0
```

**Option B: Manual commands**

```bash
# Docker Hub
docker login
docker build -t YOUR_USERNAME/ems-ibr:latest .
docker push YOUR_USERNAME/ems-ibr:latest

# GitHub Container Registry
echo "YOUR_TOKEN" | docker login ghcr.io -u YOUR_USERNAME --password-stdin
docker build -t ghcr.io/YOUR_USERNAME/ems-ibr:latest .
docker push ghcr.io/YOUR_USERNAME/ems-ibr:latest
```

### Step 2: Create Railway Services

1. **Create Railway Project** at [railway.app](https://railway.app)
2. **Add PostgreSQL**: Click "+ New" → Database → PostgreSQL
3. **Add Redis**: Click "+ New" → Database → Redis

### Step 3: Deploy from Docker Image

**Web Service:**

1. Click "+ New" → "Empty Service" → Name it `web`
2. Settings → Source → "Docker Image"
3. Enter image: `YOUR_USERNAME/ems-ibr:latest`
4. Variables → Add:
   ```
   SERVICE_TYPE=web
   SECRET_KEY=your-secret-key
   DEBUG=False
   ALLOWED_HOSTS=*.railway.app
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   ```
5. Settings → Networking → Generate Domain
6. Deploy!

**Celery Worker:**

1. Click "+ New" → "Empty Service" → Name it `celery-worker`
2. Settings → Source → "Docker Image"
3. Enter image: `YOUR_USERNAME/ems-ibr:latest` (same image)
4. Variables → Add:
   ```
   SERVICE_TYPE=worker
   SECRET_KEY=your-secret-key
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   ```
5. Deploy!

## 📋 Complete Checklist

- [ ] Install Docker locally
- [ ] Create Docker Hub or GitHub account
- [ ] Build Docker image
- [ ] Push image to registry
- [ ] Create Railway project
- [ ] Add PostgreSQL service
- [ ] Add Redis service
- [ ] Deploy web service from image
- [ ] Deploy worker service from image
- [ ] Configure environment variables
- [ ] Generate domain for web service
- [ ] Test the application

## 🔑 Required Environment Variables

### Web Service

```env
SERVICE_TYPE=web
SECRET_KEY=<generate-random-50-char-string>
DEBUG=False
ALLOWED_HOSTS=your-app.railway.app
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
DJANGO_SUPERUSER_EMAIL_1=admin@example.com
DJANGO_SUPERUSER_PASSWORD_1=SecurePassword123!
DJANGO_SUPERUSER_FIRSTNAME_1=Admin
DJANGO_SUPERUSER_LASTNAME_1=User
```

### Worker Service

```env
SERVICE_TYPE=worker
SECRET_KEY=<same-as-web-service>
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

## 🔄 Update Deployment

When you make code changes:

```bash
# 1. Rebuild image
docker build -t YOUR_USERNAME/ems-ibr:latest .

# 2. Push to registry
docker push YOUR_USERNAME/ems-ibr:latest

# 3. Railway will auto-redeploy or click "Redeploy" in Railway dashboard
```

## 🤖 Automated CI/CD (Optional)

The project includes GitHub Actions workflow (`.github/workflows/docker-publish.yml`) that automatically:

- Builds Docker image on every push to main
- Pushes to GitHub Container Registry
- Tags with version numbers from git tags

Just push to GitHub and the image is automatically built!

```bash
git add .
git commit -m "Update application"
git push origin main
# Image automatically builds and pushes to ghcr.io
```

## 🐛 Troubleshooting

**Image not found?**

- Make sure the image is public or add credentials in Railway
- Verify the image URL is correct

**Web service crashes?**

- Check `DATABASE_URL` is set correctly
- Verify `SERVICE_TYPE=web` is set
- View logs in Railway dashboard

**Worker not processing tasks?**

- Verify `SERVICE_TYPE=worker` is set
- Check `REDIS_URL` is configured
- Ensure both web and worker are running

**Generate SECRET_KEY:**

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

## 📚 More Information

See [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) for detailed documentation.

## 🎯 Architecture

```
┌──────────────────┐
│  Your Computer   │
│                  │
│  1. Build Image  │
│  2. Push to      │
│     Registry     │
└────────┬─────────┘
         │
         ▼
┌─────────────────────┐
│  Docker Registry    │
│  (Docker Hub/GHCR)  │
└────────┬────────────┘
         │
         ▼
┌────────────────────────────────┐
│         Railway                │
│                                │
│  ┌──────────┐  ┌────────────┐ │
│  │PostgreSQL│  │   Redis    │ │
│  └─────┬────┘  └──────┬─────┘ │
│        │              │        │
│  ┌─────▼──────┐  ┌────▼─────┐ │
│  │    Web     │  │  Worker  │ │
│  │  Service   │  │  Service │ │
│  │  (Django)  │  │ (Celery) │ │
│  └────────────┘  └──────────┘ │
└────────────────────────────────┘
```

---

**Ready to deploy! 🚀**
