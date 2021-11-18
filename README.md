# Nautobot Version Control App

The Nautobot Version Control app brings version control to Nautobot's database. Nautobot is an open source Network Source of Truth and Network Automation Platform. 
Nautobot provides a number of features to validate its data model and safeguard network configuration from errors. 
Adding database versioning provides another layer of assurance by enabling human review of proposed changes to production data, use of automated testing pipelines, and database rollback in the case of errors. 

The database versioning is made possible by the use of a [*Dolt*](https://github.com/dolthub/dolt) database. 
Dolt is an SQL database that you can fork, clone, branch, merge, push and pull just like a git repository.
Dolt’s *branch* and *merge* versioning model allows operators to safely modify the data model on feature branches, merging to production only after validation is complete.

## Documentation

In addition to this README file, there are docs covering the following topics:

* [Version control operations](docs/version-control-operations.md)
  * Covers common version control operations in the Version Control app
* [Common workflows](docs/workflows/common_workflows.md)
  * Covers common workflows enabled by the Version Control app
* [Design](docs/design.md)
  * Describes the technical design and implementation details of the Version Control app

## Local Dev & Test Environment

### Getting Started

Getting started with development for the Version Control plugin is pretty straightforward. 
It’s modeled directly after the development environment of Nautobot itself, and should feel very familiar to anyone with Django development experience. 
The Version Control app uses a Docker Compose environment to make it simple to manage dependencies like Dolt and Redis.

### Install Invoke

Because it is used to execute all common Docker workflow tasks, Invoke must be installed for your user environment. 
On most systems, if you're installing without root/superuser permissions, the default will install into your local user environment.
```bash
$ pip3 install invoke
```

If you run into issues, you may also deliberately tell pip3 to install into your user environment by adding the --user flag:
```bash
$ pip3 install --user invoke
```

### List Invoke Tasks

Now that you have an invoke command, list the tasks defined in tasks.py with `invoke --list`:
```bash
$ invoke --list
Available tasks:

  bandit              Run bandit to validate basic static code security analysis.
  black               Check Python code style with Black.
  build               Build Nautobot docker image.
  check-migrations    Check for missing migrations.
  cli                 Launch a bash shell inside the running Nautobot container.
  createsuperuser     Create a new Nautobot superuser account (default: "admin"), will prompt for password.
  debug               Start Nautobot and its dependencies in debug mode.
  destroy             Destroy all containers and volumes.
  flake8              Check for PEP8 compliance and other style issues.
  generate-packages   Generate all Python packages inside docker and copy the file locally under dist/.
  hadolint            Check Dockerfile for hadolint compliance and other style issues.
  load-data           Load data.
  makemigrations      Perform makemigrations operation in Django.
  migrate             Perform migrate operation in Django.
  nbshell             Launch an interactive nbshell session.
  post-upgrade        Performs Nautobot common post-upgrade operations using a single entrypoint.
  pydocstyle          Run pydocstyle to validate docstring formatting adheres to NTC defined standards.
  pylint              Run pylint code analysis.
  restart             Gracefully restart all containers.
  start               Start Nautobot and its dependencies in detached mode.
  stop                Stop Nautobot and its dependencies.
  tests               Run all tests for this plugin.
  unittest            Run Nautobot unit tests.
  unittest-coverage   Report on code test coverage as measured by 'invoke unittest'.
  vscode              Launch Visual Studio Code with the appropriate Environment variables to run in a container.
  yamllint            Run yamllint to validate formating adheres to NTC defined YAML standards.
```

### Using Docker with Invoke

A development environment can be easily started up from the root of the project using the following commands:
- invoke build - Builds Nautobot docker images
- invoke migrate - Performs database migration operation in Django
- invoke createsuperuser - Creates a superuser account for the Nautobot application
- invoke debug - Starts Docker containers for Nautobot, PostgreSQL, Redis, Celery, and the RQ worker in debug mode and attaches their output to the terminal in the foreground. You may enter Control-C to stop the containers.

Additional useful commands for the development environment:
- invoke start - Starts all Docker containers to run in the background with debug disabled
- invoke stop - Stops all containers created by invoke start


A local environment based on Docker Compose is available for development and testing as well as a sample dataset to help get started faster with Nautobot & Dolt integration.

### Initialize the Local environment

Run the following commmands to initialize the local environment
```
cp development/creds.example.env development/creds.env
invoke build
```

### Start the Local environment with a sample database

This is a good option for those who want to quickly spin up a working instance of Nautobot running the Version Control app.  
The steps below 

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


Run the following commands to Reset the Local environment and load the sample dataset again:
```
invoke stop
invoke destroy
invoke migrate
invoke load-data
invoke start
```

### Start the Local environment with an empty database

This option will simply start the local dev environment. Nautobot will have an empty database:
```
invoke migrate
invoke start
```

After few min, Nautobot will be available at `http://0.0.0.0:8080` 
You can connect with:
- Login `admin` / Password `admin`

Run the following commands to Reset the Local environment:
```
invoke stop
invoke destroy
invoke migrate
invoke start
```

## Production Installation

This section is currently under development, and the documentation is incomplete.

### Installation Considerations

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


### Configuring Nautobot to use Version Control

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

### Version Control Installation (new Nautobot install)

To be written

### Version Control Installation (migrating an existing Nautobot install)

To be written