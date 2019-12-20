"""
Django settings for openl2m project.

Generated by 'django-admin startproject' using Django 2.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import logging
import os
import socket
import platform
import sys
import warnings

from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured

# Django 2.1 requires Python 3.5+
if sys.version_info < (3, 5):
    raise RuntimeError(
        "OpenL2M requires Python 3.5 or higher (current: Python {})".format(sys.version.split()[0])
    )

# Check for configuration file
try:
    from openl2m import configuration
except ImportError:
    raise ImproperlyConfigured(
        "Configuration file is not present. Please define openl2m/openl2m/configuration.py per the documentation."
    )

VERSION = '1.0-beta(20191219)'

# Hostname
HOSTNAME = platform.node()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Database
configuration.DATABASE.update({'ENGINE': 'django.db.backends.postgresql'})
DATABASES = {
    'default': configuration.DATABASE,
}

# Import required configuration parameters
ALLOWED_HOSTS = DATABASE = SECRET_KEY = None
for setting in ['ALLOWED_HOSTS', 'DATABASE', 'SECRET_KEY']:
    try:
        globals()[setting] = getattr(configuration, setting)
    except AttributeError:
        raise ImproperlyConfigured(
            "Mandatory setting {} is missing from configuration.py.".format(setting)
        )

# Import optional configuration parameters
ADMINS = getattr(configuration, 'ADMINS', [])
BANNER_BOTTOM = getattr(configuration, 'BANNER_BOTTOM', '')
BANNER_LOGIN = getattr(configuration, 'BANNER_LOGIN', '')
BANNER_TOP = getattr(configuration, 'BANNER_TOP', '')
BASE_PATH = getattr(configuration, 'BASE_PATH', '')
if BASE_PATH:
    BASE_PATH = BASE_PATH.strip('/') + '/'  # Enforce trailing slash only
LOG_MAX_AGE = getattr(configuration, 'LOG_MAX_AGE', 180)
CORS_ORIGIN_ALLOW_ALL = getattr(configuration, 'CORS_ORIGIN_ALLOW_ALL', False)
CORS_ORIGIN_REGEX_WHITELIST = getattr(configuration, 'CORS_ORIGIN_REGEX_WHITELIST', [])
CORS_ORIGIN_WHITELIST = getattr(configuration, 'CORS_ORIGIN_WHITELIST', [])
DATE_FORMAT = getattr(configuration, 'DATE_FORMAT', 'N j, Y')
DATETIME_FORMAT = getattr(configuration, 'DATETIME_FORMAT', 'N j, Y g:i a')
DEBUG = getattr(configuration, 'DEBUG', False)
LOGGING = getattr(configuration, 'LOGGING', {})
LOGIN_TIMEOUT = getattr(configuration, 'LOGIN_TIMEOUT', 1800)
MAINTENANCE_MODE = getattr(configuration, 'MAINTENANCE_MODE', False)
MAX_PAGE_SIZE = getattr(configuration, 'MAX_PAGE_SIZE', 1000)
PAGINATE_COUNT = getattr(configuration, 'PAGINATE_COUNT', 50)
PREFER_IPV4 = getattr(configuration, 'PREFER_IPV4', False)
SESSION_FILE_PATH = getattr(configuration, 'SESSION_FILE_PATH', None)
SHORT_DATE_FORMAT = getattr(configuration, 'SHORT_DATE_FORMAT', 'Y-m-d')
SHORT_DATETIME_FORMAT = getattr(configuration, 'SHORT_DATETIME_FORMAT', 'Y-m-d H:i')
SHORT_TIME_FORMAT = getattr(configuration, 'SHORT_TIME_FORMAT', 'H:i:s')
TIME_FORMAT = getattr(configuration, 'TIME_FORMAT', 'g:i a')
TIME_ZONE = getattr(configuration, 'TIME_ZONE', 'UTC')

PORT_TOGGLE_DELAY = getattr(configuration, 'PORT_TOGGLE_DELAY', 5)
POE_TOGGLE_DELAY = getattr(configuration, 'POE_TOGGLE_DELAY', 5)

ALWAYS_ALLOW_POE_TOGGLE = getattr(configuration, 'ALWAYS_ALLOW_POE_TOGGLE', False)

CSRF_TRUSTED_ORIGINS = ALLOWED_HOSTS

SWITCH_INFO_URLS = getattr(configuration, 'SWITCH_INFO_URLS', False)
INTERFACE_INFO_URLS = getattr(configuration, 'INTERFACE_INFO_URLS', False)
VLAN_INFO_URLS = getattr(configuration, 'VLAN_INFO_URLS', False)
IP4_INFO_URLS = getattr(configuration, 'IP4_INFO_URLS', False)
IP6_INFO_URLS = getattr(configuration, 'IP6_INFO_URLS', False)
ETHERNET_INFO_URLS = getattr(configuration, 'ETHERNET_INFO_URLS', False)

ETH_FORMAT = getattr(configuration, 'ETH_FORMAT', 0)
ETH_FORMAT_UPPERCASE = getattr(configuration, 'ETH_FORMAT_UPPERCASE', 0)

IFACE_HIDE_REGEX_IFNAME = getattr(configuration, 'IFACE_HIDE_REGEX_IFNAME', '')
IFACE_HIDE_REGEX_IFDESCR = getattr(configuration, 'IFACE_HIDE_REGEX_IFDESCR', '')
IFACE_HIDE_SPEED_ABOVE = getattr(configuration, 'IFACE_HIDE_SPEED_ABOVE', 0)
IFACE_ALIAS_NOT_ALLOW_REGEX = getattr(configuration, 'IFACE_ALIAS_NOT_ALLOW_REGEX', '')
IFACE_ALIAS_KEEP_BEGINNING_REGEX = getattr(configuration, 'IFACE_ALIAS_KEEP_BEGINNING_REGEX', '')

MENU_ON_RIGHT = getattr(configuration, 'MENU_ON_RIGHT', True)
MENU_INFO_URLS = getattr(configuration, 'MENU_INFO_URLS', False)

# colors
BGCOLOR_IF_ADMIN_UP = getattr(configuration, 'BGCOLOR_IF_ADMIN_UP', "#D9FCC2")
BGCOLOR_IF_ADMIN_UP_UP = getattr(configuration, 'BGCOLOR_IF_ADMIN_UP_UP', "#ADFF2F")
BGCOLOR_IF_ADMIN_DOWN = getattr(configuration, 'BGCOLOR_IF_ADMIN_DOWN', "#FF6347")

# snmp related constants
SNMP_TIMEOUT = getattr(configuration, 'SNMP_TIMEOUT', 4)    # seconds before retry, see EasySNMP docs
SNMP_RETRIES = getattr(configuration, 'SNMP_RETRIES', 3)    # retries before fail
SNMP_MAX_REPETITIONS = getattr(configuration, 'SNMP_MAX_REPETITIONS', 10)   # SNMP get_bulk max_repetitions

# Sessions
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
if LOGIN_TIMEOUT is not None:
    if type(LOGIN_TIMEOUT) is not int or LOGIN_TIMEOUT < 0:
        raise ImproperlyConfigured(
            "LOGIN_TIMEOUT must be a positive integer (value: {})".format(LOGIN_TIMEOUT)
        )
    # Django default is 1209600 seconds (14 days)
    SESSION_COOKIE_AGE = LOGIN_TIMEOUT
if SESSION_FILE_PATH is not None:
    SESSION_ENGINE = 'django.contrib.sessions.backends.file'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ordered_model',
    'users.apps.UsersConfig',
    'switches.apps.SwitchesConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'openl2m.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # add snmp-related constants to every template, see switches/context_processors.py
                'switches.context_processors.add_variables',
            ],
        },
    },
]

WSGI_APPLICATION = 'openl2m.wsgi.application'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True


# Authentication backend, this is the default.
# it may be changed if we use ldap, see below
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]


#
# LDAP authentication (optional)
#

try:
    from openl2m import ldap_config as LDAP_CONFIG
except ImportError:
    LDAP_CONFIG = None

if LDAP_CONFIG is not None:

    # Check that django_auth_ldap is installed
    try:
        import ldap
        import django_auth_ldap
    except ImportError:
        raise ImproperlyConfigured(
            "LDAP authentication has been configured, but django-auth-ldap is not installed. Remove "
            "openl2m/ldap_config.py to disable LDAP."
        )

    # Required configuration parameters
    try:
        AUTH_LDAP_SERVER_URI = getattr(LDAP_CONFIG, 'AUTH_LDAP_SERVER_URI')
    except AttributeError:
        raise ImproperlyConfigured(
            "Required parameter AUTH_LDAP_SERVER_URI is missing from ldap_config.py."
        )

    # Optional configuration parameters
    AUTH_LDAP_ALWAYS_UPDATE_USER = getattr(LDAP_CONFIG, 'AUTH_LDAP_ALWAYS_UPDATE_USER', True)
    AUTH_LDAP_AUTHORIZE_ALL_USERS = getattr(LDAP_CONFIG, 'AUTH_LDAP_AUTHORIZE_ALL_USERS', False)
    AUTH_LDAP_BIND_AS_AUTHENTICATING_USER = getattr(LDAP_CONFIG, 'AUTH_LDAP_BIND_AS_AUTHENTICATING_USER', False)
    AUTH_LDAP_BIND_DN = getattr(LDAP_CONFIG, 'AUTH_LDAP_BIND_DN', '')
    AUTH_LDAP_BIND_PASSWORD = getattr(LDAP_CONFIG, 'AUTH_LDAP_BIND_PASSWORD', '')
    AUTH_LDAP_CACHE_TIMEOUT = getattr(LDAP_CONFIG, 'AUTH_LDAP_CACHE_TIMEOUT', 0)
    AUTH_LDAP_CONNECTION_OPTIONS = getattr(LDAP_CONFIG, 'AUTH_LDAP_CONNECTION_OPTIONS', {})
    AUTH_LDAP_DENY_GROUP = getattr(LDAP_CONFIG, 'AUTH_LDAP_DENY_GROUP', None)
    AUTH_LDAP_FIND_GROUP_PERMS = getattr(LDAP_CONFIG, 'AUTH_LDAP_FIND_GROUP_PERMS', False)
    AUTH_LDAP_GLOBAL_OPTIONS = getattr(LDAP_CONFIG, 'AUTH_LDAP_GLOBAL_OPTIONS', {})
    AUTH_LDAP_GROUP_SEARCH = getattr(LDAP_CONFIG, 'AUTH_LDAP_GROUP_SEARCH', None)
    AUTH_LDAP_GROUP_TYPE = getattr(LDAP_CONFIG, 'AUTH_LDAP_GROUP_TYPE', None)
    AUTH_LDAP_MIRROR_GROUPS = getattr(LDAP_CONFIG, 'AUTH_LDAP_MIRROR_GROUPS', None)
    AUTH_LDAP_MIRROR_GROUPS_EXCEPT = getattr(LDAP_CONFIG, 'AUTH_LDAP_MIRROR_GROUPS_EXCEPT', None)
    AUTH_LDAP_PERMIT_EMPTY_PASSWORD = getattr(LDAP_CONFIG, 'AUTH_LDAP_PERMIT_EMPTY_PASSWORD', False)
    AUTH_LDAP_REQUIRE_GROUP = getattr(LDAP_CONFIG, 'AUTH_LDAP_REQUIRE_GROUP', None)
    AUTH_LDAP_NO_NEW_USERS = getattr(LDAP_CONFIG, 'AUTH_LDAP_NO_NEW_USERS', False)
    AUTH_LDAP_START_TLS = getattr(LDAP_CONFIG, 'AUTH_LDAP_START_TLS', False)
    AUTH_LDAP_USER_QUERY_FIELD = getattr(LDAP_CONFIG, 'AUTH_LDAP_USER_QUERY_FIELD', None)
    AUTH_LDAP_USER_ATTRLIST = getattr(LDAP_CONFIG, 'AUTH_LDAP_USER_ATTRLIST', None)
    AUTH_LDAP_USER_ATTR_MAP = getattr(LDAP_CONFIG, 'AUTH_LDAP_USER_ATTR_MAP', {})
    AUTH_LDAP_USER_DN_TEMPLATE = getattr(LDAP_CONFIG, 'AUTH_LDAP_USER_DN_TEMPLATE', None)
    AUTH_LDAP_USER_FLAGS_BY_GROUP = getattr(LDAP_CONFIG, 'AUTH_LDAP_USER_FLAGS_BY_GROUP', {})
    AUTH_LDAP_USER_SEARCH = getattr(LDAP_CONFIG, 'AUTH_LDAP_USER_SEARCH', None)
    AUTH_LDAP_GROUP_TO_SWITCHGROUP_REGEX = getattr(LDAP_CONFIG, 'AUTH_LDAP_GROUP_TO_SWITCHGROUP_REGEX', None)

    # Optionally disable strict certificate checking
    if getattr(LDAP_CONFIG, 'LDAP_IGNORE_CERT_ERRORS', False):
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

    # Prepend LDAPBackend to the authentication backends list
    AUTHENTICATION_BACKENDS.insert(0, 'django_auth_ldap.backend.LDAPBackend')

    # Enable logging for django_auth_ldap
    ldap_logger = logging.getLogger('django_auth_ldap')
    ldap_logger.addHandler(logging.StreamHandler())
    ldap_logger.setLevel(logging.DEBUG)


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = BASE_DIR + '/static'
STATIC_URL = '/{}static/'.format(BASE_PATH)
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'project-static'),
)
