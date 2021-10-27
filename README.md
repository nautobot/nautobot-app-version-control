# Nautobot + Dolt

This is a work in progress and NOT officially released or supported.

## Documentation

Read the docs for [version control operations](docs/version-control-operations.md) and [common workflows](docs/workflows/common_workflows.md).

The [design](docs/design.md) documents describe the considerations and architecture for this app.

## Installation Considerations

There are some special considerations for running the Version Control app:

* The Nautobot installation MUST be running a Dolt database
* There are some [additional configurations](#configuring-nautobot-to-use-version-control) required in `nautobot_config.py`


The version control app can be installed with pip3:

```no-highlight
pip3 install git+https://github.com/nautobot/nautobot-plugin-version-control
```

> The app is compatible with Nautobot 1.1.0 and higher

To ensure the version control app is automatically re-installed during future upgrades, create a file named `local_requirements.txt` (if not already existing) in the Nautobot root directory (alongside `requirements.txt`) and list the `nautobot-plugin-version-control` package:

```no-highlight
echo nautobot-plugin-version-control >> local_requirements.txt
```

Once installed, the plugin needs to be enabled in your `nautobot_config.py`

```python
# In your nautobot_config.py
PLUGINS = [ "nautobot_plugin_version_control" ]
```


## Configuring Nautobot to use Version Control

Add this to your `nautobot_config.py`:

```python
# Dolt requires a second database using the same credentials as the default 
# database so that it may generate diffs.
DATABASES["global"] = DATABASES["default"]

# Add Dolt to your list of plugins.
PLUGINS += [
   "dolt",
]
```

Then run database migrations:

```no-highlight
$ nautobot-server migrate
```

After migrations have been run, then you must enable the `DATABASE_ROUTERS` required by Dolt to use the `default` and `global` database configurations to perform the before & after queries for generating diffs. Add this to your `nautobot_config.py` and restart Nautobot afterward:

```python
# Dolt requires a custom database router to generate the before & after queries for generating diffs.
DATABASE_ROUTERS = ["dolt.routers.GlobalStateRouter"]
```

Note that any time you need to perform database migrations (such as when upgrading Nautobot or Dolt) you **absolutely must comment out/disable `DATABASE_ROUTERS` from your `nautobot_config.py`** or you will encounter errors.

## Local Dev & Test Environment

A local environment based on Docker Compose is available for development and testing as well as a sample dataset to help get started faster with Nautobot & Dolt integration.

### Initialize the Local environment

Run the following commmands to initialize the local environment
```
cp development/creds.example.env development/creds.env
invoke build
```

### Start the Local environment with a sample database
```
invoke migrate
invoke load-data
invoke start
```

> `invoke load-data` can take up to 30 min to run and it will generate many Warning messages, these messages can be ignored.

After few min, Nautobot will be available at `http://0.0.0.0:8080` 
You can connect with either of these 2 accounts:

* Login `admin` / Password `admin`
* Login `demo` / Password `nautobot`

Run the following commands to Reset the Local environment and load the sample dataset again
```
invoke stop
invoke destroy
invoke migrate
invoke load-data
invoke start
```

### Start the Local environment with an empty database

```
invoke migrate
invoke start
```

After few min, Nautobot will be available at `http://0.0.0.0:8080` 
You can connect with:
- Login `admin` / Password `admin`

Run the following commands to Reset the Local environment
```
invoke stop
invoke destroy
invoke migrate
invoke start
```
