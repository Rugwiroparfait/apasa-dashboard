"""Environment-driven Django settings for local development and HTTPS deployment."""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("APASA_SECRET_KEY", "apasa-local-prototype-only")
DEBUG = os.environ.get("APASA_DEBUG", "true").lower() == "true"
if not DEBUG and (
    not os.environ.get("APASA_SECRET_KEY") or SECRET_KEY == "apasa-local-prototype-only"
):
    raise ValueError("Set a unique APASA_SECRET_KEY for production")
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("APASA_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(
        ","
    )
    if h.strip()
]
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "accounts",
    "evidence",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.WorkspaceAuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "apasa.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
            ]
        },
    }
]
WSGI_APPLICATION = "apasa.wsgi.application"
# CSV evidence loaders do not query the evidence database; authentication still uses it.
PUBLIC_EVIDENCE_MODE = os.environ.get("APASA_EVIDENCE_MODE", "csv")
if PUBLIC_EVIDENCE_MODE not in {"csv", "database"}:
    raise ValueError("APASA_EVIDENCE_MODE must be csv or database")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("APASA_SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
    }
}
if os.environ.get("APASA_DB_NAME"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["APASA_DB_NAME"],
            "USER": os.environ.get("APASA_DB_USER", ""),
            "PASSWORD": os.environ.get("APASA_DB_PASSWORD", ""),
            "HOST": os.environ.get("APASA_DB_HOST", "localhost"),
            "PORT": os.environ.get("APASA_DB_PORT", "5432"),
            "OPTIONS": {"connect_timeout": 3},
        }
    }
STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
PUBLIC_EVIDENCE_ROOT = BASE_DIR
TIME_ZONE = "Africa/Kigali"
USE_TZ = True

STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedStaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/workspace/"
LOGOUT_REDIRECT_URL = "/"
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_TRUSTED_ORIGINS = [
    x.strip()
    for x in os.environ.get("APASA_CSRF_TRUSTED_ORIGINS", "").split(",")
    if x.strip()
]
# Enable only behind a trusted proxy that strips client-supplied forwarding headers.
if os.environ.get("APASA_TRUST_PROXY", "false").lower() == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
