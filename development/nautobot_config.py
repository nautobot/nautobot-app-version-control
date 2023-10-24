"""Nautobot development configuration file."""
import os
import sys

from django.core.exceptions import ImproperlyConfigured
from nautobot.core.settings import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import
from nautobot.core.settings_funcs import is_truthy, parse_redis_connection

# Enforce required configuration parameters
for key in [
    # "ALLOWED_HOSTS",
    "DOLT_DB",
    "DOLT_USER",
    "DOLT_HOST",
    "DOLT_PASSWORD",
    # "REDIS_HOST",
    # "REDIS_PASSWORD",
    # "SECRET_KEY",
]:
    if not os.environ.get(key):
        raise ImproperlyConfigured(f"Required environment variable {key} is missing.")

#
# Debug
#

DEBUG = is_truthy(os.getenv("NAUTOBOT_DEBUG", False))
_TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

if DEBUG and not _TESTING:
    DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda _request: True}

    if "debug_toolbar" not in INSTALLED_APPS:  # noqa: F405
        INSTALLED_APPS.append("debug_toolbar")  # noqa: F405
    if "debug_toolbar.middleware.DebugToolbarMiddleware" not in MIDDLEWARE:  # noqa: F405
        MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405

#
# Misc. settings
#

ALLOWED_HOSTS = os.getenv("NAUTOBOT_ALLOWED_HOSTS", "").split(" ")
SECRET_KEY = os.getenv("NAUTOBOT_SECRET_KEY", "")

#
# Database
#

# Dolt database configuration. Dolt is compatible with the MySQL database backend.
# See the Django documentation for a complete list of available parameters:
#   https://docs.djangoproject.com/en/stable/ref/settings/#databases
DATABASES = {
    "default": {
        "NAME": "nautobot",  # Database name
        "USER": os.getenv("DOLT_USER", ""),  # Database username
        "PASSWORD": os.getenv("DOLT_PASSWORD", ""),  # Database password
        "HOST": os.getenv("DOLT_HOST", "localhost"),  # Database server
        "PORT": os.getenv("DOLT_PORT", ""),  # Database port (leave blank for default)
        "ENGINE": "django.db.backends.mysql",
    },
    # TODO: use `nautobot_version_control.constants.GLOBAL_STATE_DB`
    "global": {
        # TODO: use `nautobot_version_control.constants.DOLT_DEFAULT_BRANCH`
        "NAME": "nautobot",  # Database username
        "USER": os.getenv("DOLT_USER", ""),  # Database username
        "PASSWORD": os.getenv("DOLT_PASSWORD", ""),  # Database password
        "HOST": os.getenv("DOLT_HOST", "localhost"),  # Database server
        "PORT": os.getenv("DOLT_PORT", ""),  # Database port (leave blank for default)
        "ENGINE": "django.db.backends.mysql",
        "TEST": {
            "MIRROR": "default",
        },
    },
}

# # Ensure proper Unicode handling for MySQL
# if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
#     DATABASES["default"]["OPTIONS"] = {"charset": "utf8mb4"}
#
# Redis
#

# The django-redis cache is used to establish concurrent locks using Redis.
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

# Redis Cacheops
CACHEOPS_REDIS = parse_redis_connection(redis_database=1)

#
# Celery settings are not defined here because they can be overloaded with
# environment variables. By default they use `CACHES["default"]["LOCATION"]`.
#

#
# Logging
#

LOG_LEVEL = "DEBUG" if DEBUG else "INFO"

# Verbose logging during normal development operation, but quiet logging during unit test execution
if not _TESTING:
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
# Apps
#

# Enable installed Apps. Add the name of each App to the list.
PLUGINS = [
    "nautobot_version_control",
]

# Pull the list of routers from environment variable to be able to disable all routers when we are running the migrations
routers = os.getenv("DATABASE_ROUTERS", "").split(",")
DATABASE_ROUTERS = routers if routers != [""] else []

# Apps configuration settings. These settings are used by various Apps that the user may have installed.
# Each key in the dictionary is the name of an installed App and its value is a dictionary of settings.
# PLUGINS_CONFIG = {
#     'nautobot_version_control': {
#         'foo': 'bar',
#         'buzz': 'bazz'
#     }
# }
