
# Getting Started

Getting started with development for the Version Control plugin is pretty straightforward. 
It’s modeled directly after the development environment of Nautobot itself, and should feel very familiar to anyone with Django development experience. 
The Version Control plugin uses a Docker Compose environment to make it simple to manage dependencies like Dolt and Redis.

## Install Invoke

Because it is used to execute all common Docker workflow tasks, Invoke must be installed for your user environment. 
On most systems, if you're installing without root/superuser permissions, the default will install into your local user environment.
```bash
$ pip3 install invoke
```

If you run into issues, you may also deliberately tell pip3 to install into your user environment by adding the --user flag:
```bash
$ pip3 install --user invoke
```

## List Invoke Tasks

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

## Using Docker with Invoke

A development environment can be easily started up from the root of the project using the following commands:
- invoke build - Builds Nautobot docker images
- invoke migrate - Performs database migration operation in Django
- invoke createsuperuser - Creates a superuser account for the Nautobot application
- invoke debug - Starts Docker containers for Nautobot, PostgreSQL, Redis, Celery, and the RQ worker in debug mode and attaches their output to the terminal in the foreground. You may enter Control-C to stop the containers.

Additional useful commands for the development environment:
- invoke start - Starts all Docker containers to run in the background with debug disabled
- invoke stop - Stops all containers created by invoke start