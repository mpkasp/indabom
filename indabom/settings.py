import os
import io
import logging
import subprocess
import sentry_sdk
import environ
import google.auth
import google.auth.exceptions

from urllib.parse import urlparse
from google.cloud import secretmanager
from pathlib import Path
from sentry_sdk.integrations.django import DjangoIntegration

# --- Basic Setup and Environment Loading ---
## Basic Setup and Environment Loading

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent

# Setup django-environ
env = environ.Env()
env_file = BASE_DIR / '.env'

# Determine project ID from Google Cloud credentials
project_id = None
try:
    # This call is often used to establish the project context
    _, os.environ['GOOGLE_CLOUD_PROJECT'] = google.auth.default()
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    logger.info(f'Project ID: {project_id}')
except (google.auth.exceptions.DefaultCredentialsError, TypeError) as e:
    logger.warning(f'Could not determine Google Cloud Project ID: {e}')

# Load environment variables
if os.path.isfile(env_file):
    logger.info(f'Found local .env file: {env_file}')
    env.read_env(env_file)
elif project_id:
    # Load secrets from Google Secret Manager
    client = secretmanager.SecretManagerServiceClient()
    settings_name = os.environ.get("SETTINGS_NAME", "django_settings")
    logger.info(f'Fetching secrets from {settings_name} in project {project_id}')
    try:
        name = f"projects/{project_id}/secrets/{settings_name}/versions/latest"
        payload = client.access_secret_version(name=name).payload.data.decode("UTF-8")
        env.read_env(io.StringIO(payload))
    except Exception as e:
        logger.error(f"Error accessing secret manager: {e}")
        raise
else:
    # Only raise if essential for running, otherwise default to minimal settings
    logger.warning("No local .env or GOOGLE_CLOUD_PROJECT detected. Running with minimal environment.")


# --- Core Django Settings and Secret Variables ---
## Core Django Settings and Secret Variables

# Variables loaded via env.str/env.bool
DEBUG = env.bool("DEBUG", False)
ENVIRONMENT = env.str("ENVIRONMENT", "unset")
GITHUB_SHA = env.str("GITHUB_SHA", "unset")
LOCALHOST = env.bool("LOCALHOST", False)
SECRET_KEY = env.str("SECRET_KEY")

# Domain and Host Configuration
DOMAIN = 'indabom.com' if not DEBUG and not LOCALHOST else 'localhost:8000'
ROOT_DOMAIN = f'https://{DOMAIN}'

CLOUDRUN_SERVICE_URL = env("CLOUDRUN_SERVICE_URL", default=None)

# List settings
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Append Cloud Run specific settings
if CLOUDRUN_SERVICE_URL:
    logger.info(f'Cloud Run Service URL detected: {CLOUDRUN_SERVICE_URL}')
    parsed_url = urlparse(CLOUDRUN_SERVICE_URL)
    ALLOWED_HOSTS.append(parsed_url.netloc)
    CSRF_TRUSTED_ORIGINS.append(CLOUDRUN_SERVICE_URL)
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Normalize CSRF_TRUSTED_ORIGINS to include a scheme (required since Django 4+)
_SCHEMES = ("http://", "https://")
_normalized = []
for origin in CSRF_TRUSTED_ORIGINS:
    if not origin:
        continue
    o = origin.strip()
    if not o.startswith(_SCHEMES):
        o = f"https://{o}"  # Default to https
    _normalized.append(o)
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(_normalized))

if DEBUG or LOCALHOST:
    if "http://localhost:8000" not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append("http://localhost:8000")

# --- Application Configuration ---
## Application Configuration

INSTALLED_APPS = [
    'indabom',
    'bom.apps.BomConfig',

    # Django contrib apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',

    # Third-party apps
    'storages',
    'social_django',
    'materializecssform',
    'djmoney',
    'djmoney.contrib.exchange',
    'django_recaptcha',
    'anymail',
    'explorer',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
]

ROOT_URLCONF = 'indabom.urls'

# --- Templates and WSGI ---
## Templates and WSGI

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'indabom' / 'templates' / 'indabom'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'bom.context_processors.bom_config',
            ],
        },
    },
]

WSGI_APPLICATION = 'indabom.wsgi.application'

# --- Authentication and Authorization ---
## Authentication and Authorization

AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/login/'
LOGOUT_URL = '/logout/'
LOGIN_REDIRECT_URL = '/bom/'
LOGOUT_REDIRECT_URL = '/'

# Social Auth
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = env.str("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = env.str("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET")
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['email', 'profile', 'https://www.googleapis.com/auth/drive']
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {
    'access_type': 'offline',
    'approval_prompt': 'force'
}
SOCIAL_AUTH_REDIRECT_IS_HTTPS = not DEBUG
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/bom/settings?tab_anchor=file'
SOCIAL_AUTH_DISCONNECT_REDIRECT_URL = '/bom/settings?tab_anchor=file'
SOCIAL_AUTH_LOGIN_ERROR_URL = '/'

# --- Database and Cache ---
## Database and Cache

if os.environ.get("GOOGLE_CLOUD_PROJECT") and not LOCALHOST:
    logger.info(f"Using Cloud-based database configuration.")

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'HOST': env.str("DB_HOST"),
            'NAME': env.str("DB_NAME"),
            'USER': env.str("DB_USER"),
            'PASSWORD': env.str("DB_PASSWORD"),
        },
        'readonly': {
            'ENGINE': 'django.db.backends.mysql',
            'HOST': env.str("DB_HOST"),
            'NAME': env.str("DB_NAME"),
            'USER': env.str("DB_READONLY_USER"),
            'PASSWORD': env.str("DB_READONLY_PASSWORD"),
        }
    }
else:
    logger.info("Using Localhost SQLite database.")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        },
        'readonly': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

if os.environ.get("GOOGLE_CLOUD_PROJECT") and not LOCALHOST:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
            'LOCATION': '127.0.0.1:11211',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Static and Media Files (Storage) ---
## Static and Media Files (Storage)

STATIC_ROOT = BASE_DIR / "static"
MEDIA_ROOT = BASE_DIR / "media"
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
GS_BUCKET_NAME = env.str("GS_BUCKET_NAME", None)
GS_DEFAULT_ACL = env.str("GS_DEFAULT_ACL", 'publicRead')

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

if GS_BUCKET_NAME:
    logger.info(f"Using Google Cloud Storage bucket: {GS_BUCKET_NAME}")

    GCS_STORAGE_BACKEND = "storages.backends.gcloud.GoogleCloudStorage"

    STORAGES["default"] = {
        "BACKEND": GCS_STORAGE_BACKEND,
        "OPTIONS": {"bucket_name": GS_BUCKET_NAME},
    }
    STORAGES["staticfiles"] = {
        "BACKEND": GCS_STORAGE_BACKEND,
        "OPTIONS": {"bucket_name": GS_BUCKET_NAME},
    }
    # When using GCS for media, you typically don't set MEDIA_URL
    MEDIA_URL = None


# --- Email and Internationalization ---
## Email and Internationalization

# Anymail/Mailgun Configuration
MAILGUN_API_KEY = env.str("MAILGUN_API_KEY")
MAILGUN_SENDER_DOMAIN = os.environ.get('MAILGUN_SENDER_DOMAIN', f'mg.{DOMAIN}')

ANYMAIL = {
    "MAILGUN_API_KEY": MAILGUN_API_KEY,
    "MAILGUN_SENDER_DOMAIN": MAILGUN_SENDER_DOMAIN,
}
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
DEFAULT_FROM_EMAIL = "info@indabom.com"
SERVER_EMAIL = "info@indabom.com"

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- Logging ---
## Logging Configuration

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'timestamp': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
        },
    },
    'handlers': {
        'mail_admins': {
            'class': 'django.utils.log.AdminEmailHandler',
            'level': 'ERROR',
            'include_html': True,
            'formatter': 'timestamp',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'timestamp',
        },
    },
    'loggers': {
        # Root logger
        '': {
            'level': 'INFO',
            'handlers': ['console'],
        },
        # Your app loggers
        'indabom': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        },
        'bom': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        },
    },
}

# --- Third-party Specific Settings ---
## Third-party Specific Settings

# Sentry.io config
SENTRY_DSN = env.str("SENTRY_DSN")
if not LOCALHOST and SENTRY_DSN and SENTRY_DSN != 'supersecretdsn':
    try:
        release = subprocess.check_output(["git", "describe", "--always"]).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        release = 'UNKNOWN'

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        release=GITHUB_SHA,
        environment=ENVIRONMENT,
        traces_sample_rate=1.0 if DEBUG else 0.5,
        debug=DEBUG,
    )

# SQL Explorer
EXPLORER_CONNECTIONS = {'Default': 'readonly'}
EXPLORER_DEFAULT_CONNECTION = 'readonly'

# Django Money / Fixer
CURRENCY_DECIMAL_PLACES = 4
EXCHANGE_BACKEND = 'djmoney.contrib.exchange.backends.FixerBackend'
FIXER_ACCESS_KEY = env.str("FIXER_ACCESS_KEY")

# Stripe
INDABOM_STRIPE_PRICE_ID = env.str("INDABOM_STRIPE_PRICE_ID")
STRIPE_LIVE_MODE = env.bool("STRIPE_LIVE_MODE", False)
STRIPE_PUBLIC_KEY = env.str("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = env.str("STRIPE_SECRET_KEY")
STRIPE_TEST_PUBLIC_KEY = env.str("STRIPE_TEST_PUBLIC_KEY", STRIPE_PUBLIC_KEY) # Fallback to live if test not provided
STRIPE_TEST_SECRET_KEY = env.str("STRIPE_TEST_SECRET_KEY", STRIPE_SECRET_KEY) # Fallback to live if test not provided

DJSTRIPE_USE_NATIVE_JSONFIELD = True
DJSTRIPE_SUBSCRIBER_MODEL = 'bom.Organization'
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"
DJSTRIPE_WEBHOOK_SECRET = env.str("DJSTRIPE_WEBHOOK_SECRET")

def organization_request_callback(request):
    """ Gets an organization instance from request"""
    # Import models here to avoid an ``AppRegistryNotReady`` exception
    from bom.models import Organization
    return Organization.objects.get(id=request.user.bom_profile().organization)

DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK = organization_request_callback

# reCAPTCHA
RECAPTCHA_PRIVATE_KEY = env.str("RECAPTCHA_PRIVATE_KEY")
RECAPTCHA_PUBLIC_KEY = env.str("RECAPTCHA_PUBLIC_KEY")

# Other API Keys
OCTOPART_API_KEY = env.str("OCTOPART_API_KEY")
MOUSER_API_KEY = env.str("MOUSER_API_KEY")

# BOM Config
BOM_CONFIG = {
    'base_template': 'base.html',
    'octopart_api_key': env.str("OCTOPART_API_KEY"),
    'mouser_api_key': env.str("MOUSER_API_KEY"),
    'standalone_mode': False,
    'admin_dashboard': {
        'enable_autocomplete': False,
        'page_size': 50,
    }
}