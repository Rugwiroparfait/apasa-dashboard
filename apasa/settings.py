"""Environment-driven Django settings for local development and HTTPS deployment."""

from urllib.parse import urlsplit, unquote, parse_qs
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
# Local secrets stay in the ignored .env; injected process bindings take precedence.
from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env", override=False)
SECRET_KEY = os.environ.get("APASA_SECRET_KEY") or "apasa-local-prototype-only"
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
RENDER_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if RENDER_HOSTNAME and RENDER_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_HOSTNAME)
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "accounts",
    "evidence",
    "planning",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
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
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.workspace_role",
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
        "NAME": os.environ.get("APASA_SQLITE_PATH") or str(BASE_DIR / "db.sqlite3"),
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
# Render supplies an internal PostgreSQL URL. Never log its credential-bearing value.
if os.environ.get("DATABASE_URL"):
    database_url = urlsplit(os.environ["DATABASE_URL"])
    if (
        database_url.scheme not in {"postgres", "postgresql"}
        or not database_url.hostname
        or not database_url.path.strip("/")
    ):
        raise ValueError("DATABASE_URL must identify a PostgreSQL database")
    options = {"connect_timeout": 5}
    sslmode = parse_qs(database_url.query).get("sslmode", [None])[0]
    if sslmode:
        if sslmode not in {
            "disable",
            "allow",
            "prefer",
            "require",
            "verify-ca",
            "verify-full",
        }:
            raise ValueError("Unsupported PostgreSQL sslmode")
        options["sslmode"] = sslmode
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(database_url.path.lstrip("/")),
            "USER": unquote(database_url.username or ""),
            "PASSWORD": unquote(database_url.password or ""),
            "HOST": database_url.hostname,
            "PORT": str(database_url.port or 5432),
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": options,
        }
    }
if os.environ.get("RENDER") == "true" and not os.environ.get("DATABASE_URL"):
    raise ValueError(
        "Render requires DATABASE_URL; ephemeral SQLite would lose saved work"
    )
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
if RENDER_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append("https://" + RENDER_HOSTNAME)
# Render probes health over HTTP; the endpoint returns only database availability.
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
# Enable only behind a trusted proxy that strips client-supplied forwarding headers.
if os.environ.get("APASA_TRUST_PROXY", "false").lower() == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

DATA_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
NVIDIA_BASE_URL = os.environ.get(
    "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
)
APASA_AI_MODEL = os.environ.get("NVIDIA_MODEL", "openai/gpt-oss-20b")

APASA_AI_ALLOWED_MODELS = tuple(
    x.strip()
    for x in os.environ.get("APASA_AI_ALLOWED_MODELS", "openai/gpt-oss-20b").split(",")
    if x.strip()
)
APASA_AI_RPM = min(8, max(1, int(os.environ.get("APASA_AI_RPM", "8"))))
APASA_AI_RPD = min(45, max(1, int(os.environ.get("APASA_AI_RPD", "45"))))
APASA_AI_TPM = min(80000, max(2000, int(os.environ.get("APASA_AI_TPM", "80000"))))
APASA_AI_MAX_OUTPUT_TOKENS = min(
    1200, max(128, int(os.environ.get("APASA_AI_MAX_OUTPUT_TOKENS", "1200")))
)
