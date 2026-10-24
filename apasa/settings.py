"""Local public-evidence settings. PostgreSQL is optional; no users or uploads."""
from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('APASA_SECRET_KEY', 'apasa-local-prototype-only')
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
INSTALLED_APPS = ['django.contrib.staticfiles', 'django.contrib.humanize', 'evidence']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'apasa.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request']}}]
WSGI_APPLICATION = 'apasa.wsgi.application'
# CSV mode never queries the database, even when PostgreSQL is offline.
PUBLIC_EVIDENCE_MODE = os.environ.get('APASA_EVIDENCE_MODE', 'csv')
if PUBLIC_EVIDENCE_MODE not in {'csv', 'database'}:
    raise ValueError('APASA_EVIDENCE_MODE must be csv or database')
DATABASES = {}
if os.environ.get('APASA_DB_NAME'):
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['APASA_DB_NAME'],
        'USER': os.environ.get('APASA_DB_USER', ''),
        'PASSWORD': os.environ.get('APASA_DB_PASSWORD', ''),
        'HOST': os.environ.get('APASA_DB_HOST', 'localhost'),
        'PORT': os.environ.get('APASA_DB_PORT', '5432'),
        'OPTIONS': {'connect_timeout': 3},
    }}
STATIC_URL = '/static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
PUBLIC_EVIDENCE_ROOT = BASE_DIR
TIME_ZONE = 'Africa/Kigali'
USE_TZ = True
