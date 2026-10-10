import environ
from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


env = environ.Env()

# Reading .env file
environ.Env.read_env(BASE_DIR / ".env")


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    "SECRET_KEY", default="g*@kqr0q625831b)^msptwh#na3wkjbj5@rk9ac7=r+6613k^m")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=True)

# Every hostname derives from this: <slug>.<base> for schools, admin.<base>
# for the console and api.<base> for the marketing site (spec 0003).
# `ordo.app` in production, `staging.ordo.app` on Render, `localhost` locally.
PLATFORM_BASE_DOMAIN = env("PLATFORM_BASE_DOMAIN", default="localhost")

# The leading dot admits every subdomain. Any other host gets Django's 400,
# which says nothing about which schools exist. USE_X_FORWARDED_HOST stays
# off: the school always comes from the real Host header.
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[f".{PLATFORM_BASE_DOMAIN}"])
if DEBUG or env.bool("ORDO_TESTING", default=False):
    ALLOWED_HOSTS.append(".localhost")

# Django only ever sits behind Traefik (or the dashboard server's own calls),
# which says whether the browser used https. Absolute URLs (the logo) follow.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF Configuration for production
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=['http://localhost:8000']
)


# Security settings for production
if not DEBUG:
    SECURE_SSL_REDIRECT = False  # Traefik (VPS) or Render terminates TLS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True


# Application definition

# One Postgres schema per school (django-tenants). Shared apps live in the
# public schema; tenant apps get their own tables in every school's schema,
# so school data never shares a table with another school's.
SHARED_APPS = [
    "django_tenants",
    "daphne",
    "tenancy",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "corsheaders",
    "django_celery_results",
]

TENANT_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework.authtoken",
    "ems",
]

INSTALLED_APPS = SHARED_APPS + [a for a in TENANT_APPS if a not in SHARED_APPS]

TENANT_MODEL = "tenancy.School"
TENANT_DOMAIN_MODEL = "tenancy.Domain"

MIDDLEWARE = [
    # /healthz first: probes may send any Host header.
    "tenancy.middleware.HealthzMiddleware",
    "tenancy.middleware.SchoolMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "ems.middleware.AuditLogMiddleware",
]

AUTH_USER_MODEL = "ems.User"


# School hosts get core.urls; admin.<base> and api.<base> get the public one.
ROOT_URLCONF = "core.urls"
PUBLIC_SCHEMA_URLCONF = "core.urls_public"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

# Database configuration
# Postgres is required everywhere, including tests and local dev: each school
# will live in its own Postgres schema (spec 0003), which SQLite can't do.
import dj_database_url
DATABASES = {
    'default': dj_database_url.parse(env("DATABASE_URL"))
}
DATABASES["default"]["ENGINE"] = "django_tenants.postgresql_backend"
DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]

# Cache keys carry the schema name, so one school never reads another's.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "KEY_FUNCTION": "django_tenants.cache.make_key",
    },
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "/static/"

# Static files collection directory
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Directory where source static files are located (admin/DRF static only —
# the frontend is its own service). The empty `static/` dir keeps
# DEBUG=True local runs working.
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Django 5.0+ uses STORAGES instead of deprecated STATICFILES_STORAGE
# Use standard FileSystemStorage - WhiteNoise middleware will handle serving and compression
STORAGES = {
    "default": {
        # MEDIA_ROOT/<schema_name>/, resolved on every call.
        "BACKEND": "ems.cloudinary_storage.SchoolFileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# WhiteNoise configuration for better static file serving
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True if DEBUG else False

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Uploaded institution logo. Set in production: the container's own disk is
# wiped on every deploy. Format: cloudinary://<api_key>:<api_secret>@<cloud_name>
CLOUDINARY_URL = env("CLOUDINARY_URL", default="")
# Opt out of the ems.E001 deploy check: only for one instance whose
# MEDIA_ROOT is on a persistent volume.
LOCAL_MEDIA_PERSISTENT = env.bool("LOCAL_MEDIA_PERSISTENT", default=False)

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Celery Configuration. Falls back to REDIS_URL so platforms that expose a
# single Redis URL (Railway, Render, Fly, etc.) work without extra config.
CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL",
    default=env("REDIS_URL", default="redis://localhost:6379/0"),
)
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "default"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
# Beat schedules in UTC; school tasks activate the school's own zone.
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
# django_celery_results would store every school's task arguments in the
# public schema, outside isolation. BackgroundJob already records outcomes.
CELERY_TASK_IGNORE_RESULT = True
CELERY_RESULT_EXPIRES = 24 * 60 * 60  # cleans up anything that opts back in
# One message per worker process, acked when done: jobs from different
# schools start in arrival order instead of queueing behind a prefetch.
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes (hard: worker SIGKILL, uncatchable)
# Soft limit fires ~5 min earlier as a catchable SoftTimeLimitExceeded so a
# task can mark its BackgroundJob 'failed' with a useful message instead of
# being SIGKILL'd mid-run and leaving the job stuck in 'running' forever.
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes
CELERY_RESULT_EXTENDED = True

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "ems.api.pagination.DefaultPagination",
    "PAGE_SIZE": 15,
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "EXCEPTION_HANDLER": "ems.api.exceptions.handler",
}

# The dashboard (frontend/) runs on another origin and calls this API from
# the browser with a token header — no cookies, so no credentials. In
# production set this to the dashboard origin, e.g. https://ordo.app. The
# marketing site (separate repo) only calls the API server-side, so it needs
# no entry. WebSocket handshakes are checked against the same list
# (core/asgi.py).
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000"],
)
CORS_ALLOW_CREDENTIALS = False
CORS_EXPOSE_HEADERS = ["Content-Disposition"]

# Channels — falls back to REDIS_URL if CHANNEL_REDIS_URL isn't set, so
# managed-Redis providers that hand you one URL just work. Channel keys
# are namespaced under "asgi:" and don't collide with Celery's keys.
_CHANNEL_REDIS = env(
    "CHANNEL_REDIS_URL",
    default=env("REDIS_URL", default="redis://localhost:6379/0"),
)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [_CHANNEL_REDIS]},
    },
}

# The test suite runs without Redis (CI has none), so job-progress and
# notification pushes go through an in-process layer there. A fast hasher
# keeps the many test users cheap. ORDO_TESTING is set by whatever runs the
# tests (CI, or `ORDO_TESTING=1 python manage.py test`), so it holds under
# any runner rather than depending on argv.
TESTING = env.bool("ORDO_TESTING", default=False)
if TESTING:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
