# Installing the App in Nautobot

Here you will find detailed instructions on how to **install** and **configure** the App within your Nautobot environment.

!!! warning "Developer Note - Remove Me!"
    Detailed instructions on installing the App. You will need to update this section based on any additional dependencies or prerequisites.

## Prerequisites

- The plugin is compatible with Nautobot 1.5.3 and higher.
- Databases supported: PostgreSQL, MySQL

!!! note
    Please check the [dedicated page](compatibility_matrix.md) for a full compatibility matrix and the deprecation policy.

### Access Requirements

!!! warning "Developer Note - Remove Me!"
    What external systems (if any) it needs access to in order to work.

## Install Guide

!!! note
    Plugins can be installed manually or using Python's `pip`. See the [nautobot documentation](https://nautobot.readthedocs.io/en/latest/plugins/#install-the-package) for more details. The pip package name for this plugin is [`nautobot-version-control`](https://pypi.org/project/nautobot-version-control/).

The plugin is available as a Python package via PyPI and can be installed with `pip`:

```shell
pip install nautobot-version-control
```

To ensure Nautobot Version Control is automatically re-installed during future upgrades, create a file named `local_requirements.txt` (if not already existing) in the Nautobot root directory (alongside `requirements.txt`) and list the `nautobot-version-control` package:

```shell
echo nautobot-version-control >> local_requirements.txt
```

Once installed, the plugin needs to be enabled in your Nautobot configuration. The following block of code below shows the additional configuration required to be added to your `nautobot_config.py` file:

- Append `"nautobot_version_control"` to the `PLUGINS` list.
- Append the `"nautobot_version_control"` dictionary to the `PLUGINS_CONFIG` dictionary and override any defaults.

```python
# In your nautobot_config.py
PLUGINS = ["nautobot_version_control"]

# PLUGINS_CONFIG = {
#   "nautobot_version_control": {
#     ADD YOUR SETTINGS HERE
#   }
# }
```

Once the Nautobot configuration is updated, run the Post Upgrade command (`nautobot-server post_upgrade`) to run migrations and clear any cache:

```shell
nautobot-server post_upgrade
```

Then restart (if necessary) the Nautobot services which may include:

- Nautobot
- Nautobot Workers
- Nautobot Scheduler

```shell
sudo systemctl restart nautobot nautobot-worker nautobot-scheduler
```

## App Configuration

!!! warning "Developer Note - Remove Me!"
    Any configuration required to get the App set up. Edit the table below as per the examples provided.

The plugin behavior can be controlled with the following list of settings:

| Key     | Example | Default | Description                          |
| ------- | ------ | -------- | ------------------------------------- |
| `enable_backup` | `True` | `True` | A boolean to represent whether or not to run backup configurations within the plugin. |
| `platform_slug_map` | `{"cisco_wlc": "cisco_aireos"}` | `None` | A dictionary in which the key is the platform slug and the value is what netutils uses in any "network_os" parameter. |
| `per_feature_bar_width` | `0.15` | `0.15` | The width of the table bar within the overview report |

## Special Considerations

There are some special considerations for running the Version Control app:

* Nautobot 1.2.0 or later is required
* The Nautobot installation **must** be running a Dolt database
* There are some [additional configurations](#configuring-nautobot-to-use-version-control) required in `nautobot_config.py`

The version control app can be installed with pip3:

```no-highlight
pip3 install nautobot-version-control
```

To ensure the version control app is automatically reinstalled during future upgrades, create a new file named `local_requirements.txt` (if not already existing) in the Nautobot root directory (e.g. `/opt/nautobot`) to include the `nautobot-version-control` package:

```no-highlight
echo nautobot-version-control >> local_requirements.txt
```

### Configuring Nautobot to use Version Control

Add this to your `nautobot_config.py` to prepare your Nautobot settings for Dolt:

```python
# Dolt requires a second database using the same credentials as the default database so that it may 
# generate diffs.
DATABASES["global"] = DATABASES["default"]

# Dolt requires a custom database router to generate the before & after queries for generating diffs.
DATABASE_ROUTERS = ["nautobot_version_control.routers.GlobalStateRouter"]

# Because Dolt creates branches of the database, the default database sessions cannot be used. We 
# must tell Nautobot to use Redis for sessions instead. This adds a distinct cache configuration for
# using Redis cache for sessions.
# See: https://github.com/jazzband/django-redis#configure-as-session-backend
CACHES["sessions"] = {
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

# Enable the Version Control app
PLUGINS = [ "nautobot_version_control" ]
```

Then run database migrations:

```no-highlight
$ nautobot-server migrate
```
