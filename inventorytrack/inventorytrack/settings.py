"""
Django settings for inventorytrack project.
Configured for local development and Railway deployment.
"""

from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------
# In production set SECRET_KEY as a Railway environment variable.
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-m*4**a)9z!++_ge%cpoa_w645wxhq=_@le18lv88yk7^e+_d$t'
)

# DEBUG is False in production. Set DEBUG=True locally via env var if you want.
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Railway serves your app on a *.up.railway.app domain. "*" is simplest to
# start; tighten to your real domain later.
ALLOWED_HOSTS = ['*']

# Needed so DRF/JWT POSTs (login, create, etc.) aren't blocked by CSRF in prod.
CSRF_TRUSTED_ORIGINS = [
    'https://*.up.railway.app',
]


# ---------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'track_pal',
    'rest_framework',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',          # serves static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'inventorytrack.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'inventorytrack.wsgi.application'


# ---------------------------------------------------------------------
# Database
# Uses Railway's DATABASE_URL automatically when present; otherwise falls
# back to your local PostgreSQL settings.
# ---------------------------------------------------------------------
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get(
            'DATABASE_URL',
            'postgres://{user}:{password}@{host}:{port}/{name}'.format(
                user=os.environ.get('DB_USER', 'postgres'),
                password=os.environ.get('DB_PASSWORD', ''),
                host=os.environ.get('DB_HOST', 'localhost'),
                port=os.environ.get('DB_PORT', '5432'),
                name=os.environ.get('DB_NAME', 'Inventory_track'),
            )
        ),
        conn_max_age=600,
    )
}


# ---------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ---------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------
# Static files (CSS, JavaScript) — served by WhiteNoise in production
# ---------------------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------
# Django REST Framework + JWT
# ---------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}