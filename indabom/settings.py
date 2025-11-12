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

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env_file = BASE_DIR / '.env'
# db_host_override = env.str("DB_HOST", None) # for cloud build, see the comment below on DB_HOST

project_id = None
try:
    _, os.environ['GOOGLE_CLOUD_PROJECT'] = google.auth.default()
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    logger.info('project_id: {project_id}')
except google.auth.exceptions.DefaultCredentialsError as e:
    logger.error('Credentials error', e)
except TypeError as e:
    logger.error('No google cloud project found', e)

if os.path.isfile(env_file):
    logger.info(f'Found env file, using the env file: {env_file}')
    env.read_env(env_file)
elif project_id:
    client = secretmanager.SecretManagerServiceClient()
    settings_name = os.environ.get("SETTINGS_NAME")
    logger.info(f'project_id: {project_id}, settings_name: {settings_name}')
    logger.info(f'project_id: {project_id}, settings_name: {settings_name}')
    name = f"projects/{project_id}/secrets/{settings_name}/versions/latest"
    payload = client.access_secret_version(name=name).payload.data.decode("UTF-8")
    env.read_env(io.StringIO(payload))
else:
    raise Exception("No local .env or GOOGLE_CLOUD_PROJECT detected. No secrets found.")

# Set up secrets and environment variables
DEBUG = env.bool("DEBUG", False)
ENVIRONMENT = env.str("ENVIRONMENT", "unset")
GITHUB_SHA = env.str("GITHUB_SHA", "unset")
LOCALHOST = env.bool("LOCALHOST", False)
DOMAIN = 'indabom.com' if not DEBUG else 'localhost:8000'
ROOT_DOMAIN = f'https://{DOMAIN}'
SECRET_KEY = env.str("SECRET_KEY")
SENTRY_DSN = env.str("SENTRY_DSN")
GS_BUCKET_NAME_INCLUDE_PROJECT = env.bool("GS_BUCKET_NAME_INCLUDE_PROJECT", True)
# GS_BUCKET_NAME = env.str("GS_BUCKET_NAME", None) if not GS_BUCKET_NAME_INCLUDE_PROJECT else f'{project_id}_{env.str("GS_BUCKET_NAME", None)}'
GS_BUCKET_NAME = env.str("GS_BUCKET_NAME", None)
GS_DEFAULT_ACL = env.str("GS_DEFAULT_ACL", 'publicRead')
DB_HOST = env.str("DB_HOST") # if db_host_override is not None else db_host_override # for cloud build to override db host due to private ip challenges
DB_USER = env.str("DB_USER")
DB_PASSWORD = env.str("DB_PASSWORD")
DB_NAME = env.str("DB_NAME")
DB_READONLY_USER = env.str("DB_READONLY_USER")
DB_READONLY_PASSWORD = env.str("DB_READONLY_PASSWORD")
OCTOPART_API_KEY = env.str("OCTOPART_API_KEY")
MOUSER_API_KEY = env.str("MOUSER_API_KEY")
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = env.str("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = env.str("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET")
MAILGUN_API_KEY = env.str("MAILGUN_API_KEY")
MAILGUN_SENDER_DOMAIN = os.environ.get('MAILGUN_SENDER_DOMAIN', f'mg.{DOMAIN}')
RECAPTCHA_PRIVATE_KEY = env.str("RECAPTCHA_PRIVATE_KEY")
RECAPTCHA_PUBLIC_KEY = env.str("RECAPTCHA_PUBLIC_KEY")
INDABOM_STRIPE_PRICE_ID = env.str("INDABOM_STRIPE_PRICE_ID")
STRIPE_TEST_PUBLIC_KEY = env.str("STRIPE_PUBLIC_KEY")
STRIPE_TEST_SECRET_KEY = env.str("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = env.str("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = env.str("STRIPE_SECRET_KEY")
STRIPE_LIVE_MODE = env.bool("STRIPE_LIVE_MODE", False)
DJSTRIPE_WEBHOOK_SECRET = env.str("DJSTRIPE_WEBHOOK_SECRET")
FIXER_ACCESS_KEY = env.str("FIXER_ACCESS_KEY")
CLOUDRUN_SERVICE_URL = env("CLOUDRUN_SERVICE_URL", default=None)
try:
    ALLOWED_HOSTS = env.str("ALLOWED_HOSTS", None).split(',')
except AttributeError:
    ALLOWED_HOSTS = []
try:
    CSRF_TRUSTED_ORIGINS = env.str("CSRF_TRUSTED_ORIGINS", None).split(',')
except AttributeError:
    CSRF_TRUSTED_ORIGINS = []

if CLOUDRUN_SERVICE_URL:
    logger.info(f'Cloud run service url: {CLOUDRUN_SERVICE_URL}')
    ALLOWED_HOSTS.append(urlparse(CLOUDRUN_SERVICE_URL).netloc)
    CSRF_TRUSTED_ORIGINS.append(CLOUDRUN_SERVICE_URL)
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Django 4+/5+ require scheme in CSRF_TRUSTED_ORIGINS; normalize values from env
_SCHEMES = ("http://", "https://")
_normalized = []
for origin in CSRF_TRUSTED_ORIGINS:
    if not origin:
        continue
    o = origin.strip()
    if not o.startswith(_SCHEMES):
        # Default to https when scheme not provided
        o = f"https://{o}"
    _normalized.append(o)
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(_normalized))  # de-dupe, preserve order

if DEBUG or LOCALHOST:
    # Ensure local dev origin present
    if "http://localhost:8000" not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append("http://localhost:8000")

# Sentry.io config
if not LOCALHOST and SENTRY_DSN != 'supersecretdsn':
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


# Application definition

INSTALLED_APPS = [
    'indabom',
    'bom.apps.BomConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
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

AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

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
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
# log_file_path = '/var/log/indabom/django.log' if not DEBUG else './django.log'

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
            # But the emails are plain text by default - HTML is nicer
            'include_html': True,
            'formatter': 'timestamp',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'timestamp',
        },
    },
    'loggers': {
        # Again, default Django configuration to email unhandled exceptions
        # 'django.request': {
        #     'handlers': ['mail_admins'],
        #     'level': 'ERROR',
        #     'propagate': True,
        # },
        # 'django.db.backends': {
        #     'level': 'DEBUG',
        # },
        # # Might as well log any errors anywhere else in Django
        # 'django': {
        #     'handlers': ['console'],
        #     'level': 'INFO',
        #     'propagate': False,
        # },
        '': {
            'level': 'INFO',
            'handlers': ['console'],
        },
        'indabom': {
            'handlers': ['console'],
            'level': 'INFO',  # Or maybe INFO or DEBUG
            'propagate': False
        },
        'bom': {
            'handlers': ['console'],
            'level': 'INFO',  # Or maybe INFO or DEBUG
            'propagate': False
        },
    },
}

if os.environ.get("GOOGLE_CLOUD_PROJECT", None) and not LOCALHOST:
    logger.info(f"[GOOGLE_CLOUD_PROJECT] Google cloud project, host: {DB_HOST}, user: {DB_USER}, name: {DB_NAME}")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'HOST': DB_HOST,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'NAME': DB_NAME,
        },
        'readonly': {
            'ENGINE': 'django.db.backends.mysql',
            'HOST': DB_HOST,
            'USER': DB_READONLY_USER,
            'PASSWORD': DB_READONLY_PASSWORD,
            'NAME': DB_NAME,
        }
    }
else:
    print("Localhost database being used.")
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

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

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
USE_L10N = True
USE_TZ = True

STATIC_ROOT = BASE_DIR / "static"
MEDIA_ROOT = BASE_DIR / "media"
STATIC_URL = "/static/"
MEDIA_URL = "/media/"

if GS_BUCKET_NAME:
    logger.info(f"GS_BUCKET_NAME: {GS_BUCKET_NAME}")

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
            "OPTIONS": {
                "bucket_name": GS_BUCKET_NAME,
            },
        },
        "staticfiles": {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
            "OPTIONS": {
                "bucket_name": GS_BUCKET_NAME,
            },
        },
    }

    # Let the backend construct media URLs (public or signed depending on bucket policy)
    MEDIA_URL = None

LOGIN_URL = '/login/'
LOGOUT_URL = '/logout/'

LOGIN_REDIRECT_URL = '/bom/'
LOGOUT_REDIRECT_URL = '/'

# SQL Explorer
EXPLORER_CONNECTIONS = {'Default': 'readonly'}
EXPLORER_DEFAULT_CONNECTION = 'readonly'

# Social Auth
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['email', 'profile', 'https://www.googleapis.com/auth/drive']
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {
    'access_type': 'offline',
    'approval_prompt': 'force'  # forces storage of refresh token
}
SOCIAL_AUTH_REDIRECT_IS_HTTPS = not DEBUG
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/bom/settings?tab_anchor=file'
SOCIAL_AUTH_DISCONNECT_REDIRECT_URL = '/bom/settings?tab_anchor=file'
SOCIAL_AUTH_LOGIN_ERROR_URL = '/'

CURRENCY_DECIMAL_PLACES = 4
EXCHANGE_BACKEND = 'djmoney.contrib.exchange.backends.FixerBackend'

# Stripe
DJSTRIPE_USE_NATIVE_JSONFIELD = True
DJSTRIPE_SUBSCRIBER_MODEL = 'bom.Organization'
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"


def organization_request_callback(request):
    """ Gets an organization instance from request"""

    from bom.models import Organization  # Import models here to avoid an ``AppRegistryNotReady`` exception
    return Organization.objects.get(id=request.user.bom_profile().organization)


DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK = organization_request_callback

BOM_CONFIG = {
    'base_template': 'base.html',
    'octopart_api_key': OCTOPART_API_KEY,
    'mouser_api_key': MOUSER_API_KEY,
    'standalone_mode': False,
    'admin_dashboard': {
        'enable_autocomplete': False,
        'page_size': 50,
    }
}
