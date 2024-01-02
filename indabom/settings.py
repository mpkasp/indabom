"""
Django settings for indabom project.

Generated by 'django-admin startproject' using Django 2.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
import io
import subprocess
import sentry_sdk
import environ
import google.auth

from urllib.parse import urlparse
from google.cloud import secretmanager
from pathlib import Path
from sentry_sdk.integrations.django import DjangoIntegration

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env_file = os.path.join(BASE_DIR, '.env')

# Attempt to load the Project ID into the environment, safely failing on error.
try:
    _, os.environ['GOOGLE_CLOUD_PROJECT'] = google.auth.default()
except google.auth.exceptions.DefaultCredentialsError:
    pass
except TypeError as e:
    print('No google cloud project found.', e)

if os.path.isfile(env_file):
    # Use a local secret file, if provided
    env.read_env(env_file)
elif os.environ.get("GOOGLE_CLOUD_PROJECT", None):
    # Pull secrets from Secret Manager
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")

    client = secretmanager.SecretManagerServiceClient()
    settings_name = os.environ.get("SETTINGS_NAME", "django_settings")
    name = f"projects/{project_id}/secrets/{settings_name}/versions/latest"
    payload = client.access_secret_version(name=name).payload.data.decode("UTF-8")

    env.read_env(io.StringIO(payload))
else:
    raise Exception("No local .env or GOOGLE_CLOUD_PROJECT detected. No secrets found.")

# Set up secrets and environment variables
LOCALHOST = env.bool("LOCALHOST", False)
SECRET_KEY = env.str("SECRET_KEY")
DEBUG = env.bool("DEBUG", False)
SENTRY_DSN = env.str("SENTRY_DSN")
GS_BUCKET_NAME = env.str("GS_BUCKET_NAME", None) # for django-storages, dont change
GS_DEFAULT_ACL = env.str("GS_DEFAULT_ACL", 'publicRead')
DB_HOST = env.str("DB_HOST")
DB_USER = env.str("DB_USER")
DB_PASSWORD = env.str("DB_PASSWORD")
DB_NAME = env.str("DB_NAME")
DB_READONLY_USER = env.str("DB_READONLY_USER")
DB_READONLY_PASSWORD = env.str("DB_READONLY_PASSWORD")
OCTOPART_API_KEY = env.str("OCTOPART_API_KEY")
MOUSER_API_KEY = env.str("MOUSER_API_KEY")
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = env.str("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = env.str("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET")
SENDGRID_API_KEY = env.str("SENDGRID_API_KEY")
RECAPTCHA_PRIVATE_KEY = env.str("RECAPTCHA_PRIVATE_KEY")
RECAPTCHA_PUBLIC_KEY = env.str("RECAPTCHA_PUBLIC_KEY")
INDABOM_STRIPE_PRICE_ID = env.str("INDABOM_STRIPE_PRICE_ID")
STRIPE_TEST_PUBLIC_KEY = env.str("STRIPE_PUBLIC_KEY")
STRIPE_TEST_SECRET_KEY = env.str("STRIPE_SECRET_KEY")
STRIPE_PUBLIC_KEY = env.str("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = env.str("STRIPE_SECRET_KEY")
STRIPE_LIVE_MODE = env.bool("STRIPE_LIVE_MODE", False)
DJSTRIPE_WEBHOOK_SECRET = env.str("DJSTRIPE_WEBHOOK_SECRET")

CLOUDRUN_SERVICE_URL = env("CLOUDRUN_SERVICE_URL", default=None)
if CLOUDRUN_SERVICE_URL:
    ALLOWED_HOSTS = [urlparse(CLOUDRUN_SERVICE_URL).netloc]
    CSRF_TRUSTED_ORIGINS = [CLOUDRUN_SERVICE_URL]
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
else:
    ALLOWED_HOSTS = ["*"]

# Sentry.io config
if not LOCALHOST:
    try:
        release = subprocess.check_output(["git", "describe", "--always"]).strip()
    except:
        release = 'UNKNOWN'

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        release=release,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production,
        traces_sample_rate=1.0,
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
    'captcha',
    'djstripe',
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
    'social_core.backends.google.GoogleOpenId',
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.google.GoogleOAuth',
    'django.contrib.auth.backends.ModelBackend',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'indabom/templates/indabom')],
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
        # Include the default Django email handler for errors
        # This is what you'd get without configuring logging at all.
        'mail_admins': {
            'class': 'django.utils.log.AdminEmailHandler',
            'level': 'ERROR',
            # But the emails are plain text by default - HTML is nicer
            'include_html': True,
            'formatter': 'timestamp',
        },
        # Log to a text file that can be rotated by logrotate
        # 'logfile': {
        #     'class': 'logging.handlers.WatchedFileHandler',
        #     'filename': log_file_path,
        #     'formatter': 'timestamp',
        # },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'timestamp',
        },
    },
    'loggers': {
        # Again, default Django configuration to email unhandled exceptions
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.db.backends': {
            'level': 'DEBUG',
        },
        # Might as well log any errors anywhere else in Django
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
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

if CLOUDRUN_SERVICE_URL:
    print("[CLOUDRUN_SERVICE_URL] Cloud Run App")
    # Running on production App Engine, so connect to Google Cloud SQL using
    # the unix socket at /cloudsql/<your-cloudsql-connection string>
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
    # Running locally so connect to either a local MySQL instance or connect
    # to Cloud SQL via the proxy.  To start the proxy via command line:
    #    $ cloud_sql_proxy -instances=[INSTANCE_CONNECTION_NAME]=tcp:3306
    # See https://cloud.google.com/sql/docs/mysql-connect-proxy
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

# AUTH_USER_MODEL = 'indabom.User'

EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

ROOT_DOMAIN = 'https://indabom.com' if not DEBUG else 'http://localhost:8000'

# Storage - Google CLoud Storage if in cloud, else path if local
STATIC_URL = "/static/"
MEDIA_URL = '/media/'
if GS_BUCKET_NAME:
    DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
    STATICFILES_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
else:
    STATIC_ROOT = os.path.join(BASE_DIR, "static/")
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')

LOGIN_URL = '/login/'
LOGOUT_URL = '/logout/'

LOGIN_REDIRECT_URL = '/bom/'
LOGOUT_REDIRECT_URL = '/'

# SQL Explorer
EXPLORER_CONNECTIONS = {'Default': 'default'}
EXPLORER_DEFAULT_CONNECTION = 'default'


SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['email', 'profile', 'https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/plus.login']
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
    'admin_dashboard': {
        'enable_autocomplete': False,
        'page_size': 50,
    }
}
