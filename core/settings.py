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

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS",
                         default=['ems-ibr.onrender.com', 'localhost', '127.0.0.1'])

# CSRF Configuration for production
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=['http://localhost:8000']
)


# Security settings for production
if not DEBUG:
    SECURE_SSL_REDIRECT = False  # Railway handles SSL
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True


# Application definition

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_celery_results",
    "ems",
]

MIDDLEWARE = [
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


ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # In prod, the Docker build copies the React app's index.html into
        # frontend/dist/. Catchall URL renders it as a Django template so the
        # SPA boots from any unrecognised path.
        "DIRS": [BASE_DIR / "frontend" / "dist"],
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
# Use PostgreSQL if DATABASE_URL is provided, otherwise fallback to SQLite
if env("DATABASE_URL", default=None):
    # PostgreSQL Database Configuration (for production)
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(env("DATABASE_URL"))
    }
else:
    # Fallback to SQLite for development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
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

# Directory where source static files are located. The React app's compiled
# bundle (frontend/dist) is also collected so WhiteNoise can serve it under
# /static/. The empty `static/` dir keeps DEBUG=True local runs working
# even before the frontend has been built.
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
_FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    STATICFILES_DIRS.append(_FRONTEND_DIST)

# Django 5.0+ uses STORAGES instead of deprecated STATICFILES_STORAGE
# Use standard FileSystemStorage - WhiteNoise middleware will handle serving and compression
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
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
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
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

# CORS for the Vite dev server and any deployed frontend origin. In the
# bundled-frontend production deploy, the SPA is same-origin so CORS is not
# strictly required — but the dev defaults below are kept so `npm run dev`
# against a local Django server works out of the box.
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
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
