"""Nautobot development configuration file."""
import os
import sys

from nautobot.core.settings import *  # noqa: F403  # pylint: disable=wildcard-import,unused-wildcard-import
from nautobot.core.settings_funcs import is_truthy, parse_redis_connection

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

nautobot_db_engine = os.getenv("NAUTOBOT_DB_ENGINE", "django.db.backends.mysql")

# Dolt database configuration. Dolt is compatible with the MySQL database backend.
# See the Django documentation for a complete list of available parameters:
#   https://docs.djangoproject.com/en/stable/ref/settings/#databases
DATABASES = {
    "default": {
        "NAME": os.getenv("NAUTOBOT_DB_NAME", "nautobot"),  # Database name
        "USER": os.getenv("NAUTOBOT_DB_USER", ""),  # Database username
        "PASSWORD": os.getenv("NAUTOBOT_DB_PASSWORD", ""),  # Database password
        "HOST": os.getenv("NAUTOBOT_DB_HOST", "localhost"),  # Database server
        "PORT": os.getenv("NAUTOBOT_DB_PORT", "3306"),  # Database port
        "CONN_MAX_AGE": int(os.getenv("NAUTOBOT_DB_TIMEOUT", 300)),  # Database timeout
        "ENGINE": nautobot_db_engine,
        "OPTIONS": {"charset": "utf8mb4"},
    },
    "global": {
        "NAME": os.getenv("NAUTOBOT_DB_NAME", "nautobot"),  # Database name
        "USER": os.getenv("NAUTOBOT_DB_USER", ""),  # Database username
        "PASSWORD": os.getenv("NAUTOBOT_DB_PASSWORD", ""),  # Database password
        "HOST": os.getenv("NAUTOBOT_DB_HOST", "localhost"),  # Database server
        "PORT": os.getenv("NAUTOBOT_DB_PORT", "3306"),  # Database port
        "CONN_MAX_AGE": int(os.getenv("NAUTOBOT_DB_TIMEOUT", 300)),  # Database timeout
        "ENGINE": nautobot_db_engine,
        "OPTIONS": {"charset": "utf8mb4"},
        "TEST": {
            "MIRROR": "default",
        },
    },
}

# Ensure proper Unicode handling for MySQL
if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
    DATABASES["default"]["OPTIONS"] = {"charset": "utf8mb4"}


#
# Redis
#

# Because Dolt creates branches of the database, the default database sessions cannot be used. We
# must tell Nautobot to use Redis for sessions instead. This adds a distinct cache configuration for
# using Redis cache for sessions.
# See: https://github.com/jazzband/django-redis#configure-as-session-backend
CACHES["sessions"] = {  # noqa: F405
    "BACKEND": "django_redis.cache.RedisCache",
    "LOCATION": parse_redis_connection(redis_database=2),
    "TIMEOUT": 300,
    "OPTIONS": {
        "CLIENT_CLASS": "django_redis.client.DefaultClient",
    },
}

# Use the sessions alias defined in CACHES for sessions caching
SESSION_CACHE_ALIAS = "sessions"

# Use the Redis cache as the session engine
SESSION_ENGINE = "django.contrib.sessions.backends.cache"

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
                "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s : %(message)s",
                "datefmt": "%H:%M:%S",
            },
            "verbose": {
                "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-20s %(filename)-15s %(funcName)30s() : %(message)s",
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
PLUGINS = ["nautobot_version_control"]

# Apps configuration settings. These settings are used by various Apps that the user may have installed.
# Each key in the dictionary is the name of an installed App and its value is a dictionary of settings.
# PLUGINS_CONFIG = {
#     'nautobot_version_control': {
#         'foo': 'bar',
#         'buzz': 'bazz'
#     }
# }

# add SSL options if DOLT_SSL_CA is set
dolt_ssl_ca = os.getenv("DOLT_SSL_CA", None)
if dolt_ssl_ca:
    options = {"ssl": {"ca": dolt_ssl_ca}}
    DATABASES["default"]["OPTIONS"] = options
    DATABASES["global"]["OPTIONS"] = options

# Pull the list of routers from environment variable to be able to disable all routers when we are running the migrations
routers = os.getenv("DATABASE_ROUTERS", "").split(",")
DATABASE_ROUTERS = routers if routers != [""] else []
