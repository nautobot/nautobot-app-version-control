"""Nautobot development configuration file."""
# pylint: disable=invalid-envvar-default
import os
import sys

from nautobot.core.settings import *  # noqa: F403
from nautobot.core.settings_funcs import parse_redis_connection


#
# Misc. settings
#

ALLOWED_HOSTS = os.getenv("NAUTOBOT_ALLOWED_HOSTS", "").split(" ")
SECRET_KEY = os.getenv("NAUTOBOT_SECRET_KEY", "")

nautobot_db_engine = os.getenv("NAUTOBOT_DB_ENGINE", "django.db.backends.mysql")
default_db_settings = {
    "django.db.backends.postgresql": {
        "NAUTOBOT_DB_PORT": "5432",
    },
    "django.db.backends.mysql": {
        "NAUTOBOT_DB_PORT": "3306",
    },
}

OPTIONS = {"charset": "utf8mb4"}
NAUTOBOT_USE_HOSTED_DOLT = os.getenv("NAUTOBOT_USE_HOSTED_DOLT", "false").lower() == "true"
# If NAUTOBOT_USE_HOSTED_DOLT is set to true, then we will use the hosted dolt database
if NAUTOBOT_USE_HOSTED_DOLT:
    NAUTOBOT_DB_HOST = os.getenv("NAUTOBOT_HOSTED_DB_HOST", "")
    NAUTOBOT_DB_USER = os.getenv("NAUTOBOT_HOSTED_DB_USER", "")
    NAUTOBOT_DB_PASSWORD = os.getenv("NAUTOBOT_HOSTED_DB_PASSWORD", "")
    OPTIONS["ssl"] = {"ca": "/opt/nautobot/hosted_ca.pem" }
else:
    NAUTOBOT_DB_HOST = os.getenv("NAUTOBOT_DB_HOST", "localhost")
    NAUTOBOT_DB_USER = os.getenv("NAUTOBOT_DB_USER", "")
    NAUTOBOT_DB_PASSWORD = os.getenv("NAUTOBOT_DB_PASSWORD", "")


# Dolt database configuration. Dolt is compatible with the MySQL database backend.
# See the Django documentation for a complete list of available parameters:
#   https://docs.djangoproject.com/en/stable/ref/settings/#databases
DATABASES = {
    "default": {
        "NAME": os.getenv("NAUTOBOT_DB_NAME", "nautobot"),  # Database name
        "HOST": NAUTOBOT_DB_HOST,  # Database server
        "USER": NAUTOBOT_DB_USER,  # Database username
        "PASSWORD": NAUTOBOT_DB_PASSWORD,  # Database password
        "PORT": os.getenv(
            "NAUTOBOT_DB_PORT", default_db_settings[nautobot_db_engine]["NAUTOBOT_DB_PORT"]
        ),  # Database port, default to postgres
        "CONN_MAX_AGE": int(os.getenv("NAUTOBOT_DB_TIMEOUT", 300)),  # Database timeout
        "ENGINE": nautobot_db_engine,
        "OPTIONS": OPTIONS,
    },
    "global": {
        "NAME": os.getenv("NAUTOBOT_DB_NAME", "nautobot"),  # Database name
        "HOST": NAUTOBOT_DB_HOST,  # Database server
        "USER": NAUTOBOT_DB_USER,  # Database username
        "PASSWORD": NAUTOBOT_DB_PASSWORD,  # Database password
        "PORT": os.getenv(
            "NAUTOBOT_DB_PORT", default_db_settings[nautobot_db_engine]["NAUTOBOT_DB_PORT"]
        ),  # Database port, default to postgres
        "CONN_MAX_AGE": int(os.getenv("NAUTOBOT_DB_TIMEOUT", 300)),  # Database timeout
        "ENGINE": nautobot_db_engine,
        "TEST": {
            "MIRROR": "default",
        },
        "OPTIONS": OPTIONS,
    }
}

#
# Debug
#

DEBUG = True
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

# Django Debug Toolbar
DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda _request: DEBUG and not TESTING}

if DEBUG and "debug_toolbar" not in INSTALLED_APPS:  # noqa: F405
    INSTALLED_APPS.append("debug_toolbar")  # noqa: F405
if DEBUG and "debug_toolbar.middleware.DebugToolbarMiddleware" not in MIDDLEWARE:  # noqa: F405
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405

#
# Logging
#

LOG_LEVEL = "DEBUG" if DEBUG else "INFO"

# Verbose logging during normal development operation, but quiet logging during unit test execution
if not TESTING:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "normal": {
                "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s :\n  %(message)s",
                "datefmt": "%H:%M:%S",
            },
            "verbose": {
                "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-20s %(filename)-15s %(funcName)30s() :\n  %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "normal_console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "normal",
            },
            "verbose_console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
        },
        "loggers": {
            "django": {"handlers": ["normal_console"], "level": "INFO"},
            "nautobot": {
                "handlers": ["verbose_console" if DEBUG else "normal_console"],
                "level": LOG_LEVEL,
            },
        },
    }

#
# Redis
#

# The django-redis cache is used to establish concurrent locks using Redis. The
# django-rq settings will use the same instance/database by default.
#
# This "default" server is now used by RQ_QUEUES.
# >> See: nautobot.core.settings.RQ_QUEUES
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": parse_redis_connection(redis_database=0),
        "TIMEOUT": 300,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# RQ_QUEUES is not set here because it just uses the default that gets imported
# up top via `from nautobot.core.settings import *`.

# Redis Cacheops
CACHEOPS_REDIS = parse_redis_connection(redis_database=1)

#
# Celery settings are not defined here because they can be overloaded with
# environment variables. By default they use `CACHES["default"]["LOCATION"]`.
#

# Enable installed plugins. Add the name of each plugin to the list.
PLUGINS = ["nautobot_version_control"]

# Plugins configuration settings. These settings are used by various plugins that the user may have installed.
# Each key in the dictionary is the name of an installed plugin and its value is a dictionary of settings.
# PLUGINS_CONFIG = {
#     'nautobot_version_control': {
#         'foo': 'bar',
#         'buzz': 'bazz'
#     }
# }

# Pull the list of routers from environment variable to be able to disable all routers when we are running the migrations
routers = os.getenv("DATABASE_ROUTERS", "").split(",")
DATABASE_ROUTERS = routers if routers != [""] else []

# The length of time (in seconds) for which a user will remain logged into the web UI before being prompted to
# re-authenticate. (Default: 1209600 [14 days])
SESSION_COOKIE_AGE = 1209600  # 2 weeks, in seconds

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

# By default, Nautobot will store session data in the database. Alternatively, a file path can be specified here to use
# local file storage instead. (This can be useful for enabling authentication on a standby instance with read-only
# database access.) Note that the user as which Nautobot runs must have read and write permissions to this path.
SESSION_FILE_PATH = None
