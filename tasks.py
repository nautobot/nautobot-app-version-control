"""Tasks for use with Invoke.

(c) 2020-2021 Network To Code
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import time
from distutils.util import strtobool
from invoke import Collection, task as invoke_task
import os
import subprocess

def is_truthy(arg):
    """Convert "truthy" strings into Booleans.

    Examples:
        >>> is_truthy('yes')
        True
    Args:
        arg (str): Truthy string (True values are y, yes, t, true, on and 1; false values are n, no,
        f, false, off and 0. Raises ValueError if val is anything else.
    """
    if isinstance(arg, bool):
        return arg
    return bool(strtobool(arg))


# Use pyinvoke configuration for default values, see http://docs.pyinvoke.org/en/stable/concepts/configuration.html
# Variables may be overwritten in invoke.yml or by the environment variables INVOKE_NAUTOBOT_VERSION_CONTROL_xxx
namespace = Collection("nautobot_version_control")
namespace.configure(
    {
        "nautobot_version_control": {
            "nautobot_ver": "latest",
            "project_name": "nautobot_version_control",
            "python_ver": "3.8",
            "local": False,
            "compose_dir": os.path.join(os.path.dirname(__file__), "development"),
            "compose_files": [
                "docker-compose.base.yml",
                "docker-compose.redis.yml",
                "docker-compose.dolt.yml",
                "docker-compose.dev.yml",
            ],
            "hosted_compose_files": [
                "docker-compose.hosted-base.yml",
                "docker-compose.redis.yml",
                "docker-compose.dev.yml",
            ],
            "compose_http_timeout": "86400",
        }
    }
)


def task(function=None, *args, **kwargs):
    """Task decorator to override the default Invoke task decorator and add each task to the invoke namespace."""

    def task_wrapper(function=None):
        """Wrapper around invoke.task to add the task to the namespace as well."""
        if args or kwargs:
            task_func = invoke_task(*args, **kwargs)(function)
        else:
            task_func = invoke_task(function)
        namespace.add_task(task_func)
        return task_func

    if function:
        # The decorator was called with no arguments
        return task_wrapper(function)
    # The decorator was called with arguments
    return task_wrapper


def docker_compose(context, command, **kwargs):
    """Helper function for running a specific docker-compose command with all appropriate parameters and environment.

    Args:
        context (obj): Used to run specific commands
        command (str): Command string to append to the "docker-compose ..." command, such as "build", "up", etc.
        **kwargs: Passed through to the context.run() call.
    """
    build_env = {
        # Note: 'docker-compose logs' will stop following after 60 seconds by default,
        # so we are overriding that by setting this environment variable.
        "COMPOSE_HTTP_TIMEOUT": context.nautobot_version_control.compose_http_timeout,
        "NAUTOBOT_VER": context.nautobot_version_control.nautobot_ver,
        "PYTHON_VER": context.nautobot_version_control.python_ver,
    }
    compose_command_tokens = [
        "docker-compose",
        f"--project-name {context.nautobot_version_control.project_name}",
        f'--project-directory "{context.nautobot_version_control.compose_dir}"',
    ]

    use_hosted_dolt = kwargs.pop("use_hosted_dolt", False)
    compose_files = context.nautobot_version_control.compose_files
    if use_hosted_dolt:
        compose_files = context.nautobot_version_control.hosted_compose_files

    for compose_file in compose_files:
        compose_file_path = os.path.join(context.nautobot_version_control.compose_dir, compose_file)
        compose_command_tokens.append(f' -f "{compose_file_path}"')

    compose_command_tokens.append(command)

    # If `service` was passed as a kwarg, add it to the end.
    service = kwargs.pop("service", None)
    if service is not None:
        compose_command_tokens.append(service)

    compose_command = " ".join(compose_command_tokens)

    print(f'Running docker-compose command "{compose_command}"')
    return context.run(compose_command, env=build_env, **kwargs)


def run_command(context, command, **kwargs):
    """Wrapper to run a command locally or inside the nautobot container."""
    if is_truthy(context.nautobot_version_control.local):
        context.run(command, **kwargs)
    else:
        # Check if nautobot is running, no need to start another nautobot container to run a command
        docker_compose_status = "ps --services --filter status=running"
        results = docker_compose(context, docker_compose_status, hide="out", **kwargs)
        if "nautobot" in results.stdout:
            compose_command = f"exec nautobot {command}"
        else:
            compose_command = f"run --entrypoint '{command}' nautobot"

        docker_compose(context, compose_command, pty=True, **kwargs)


# ------------------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------------------
@task(
    help={
        "force_rm": "Always remove intermediate containers",
        "cache": "Whether to use Docker's cache when building the image (defaults to enabled)",
    }
)
def build(context, force_rm=False, cache=True, use_hosted_dolt=False):
    """Build Nautobot docker image."""
    command = "build"

    if not cache:
        command += " --no-cache"
    if force_rm:
        command += " --force-rm"

    print(f"Building Nautobot with Python {context.nautobot_version_control.python_ver}...")
    docker_compose(context, command, use_hosted_dolt=use_hosted_dolt)


@task
def generate_packages(context):
    """Generate all Python packages inside docker and copy the file locally under dist/."""
    command = "poetry build"
    run_command(context, command)


# ------------------------------------------------------------------------------
# START / STOP / DEBUG
# ------------------------------------------------------------------------------
@task
def debug(context, service=None):
    """Start Nautobot and its dependencies in debug mode."""
    print("Starting Nautobot in debug mode...")
    docker_compose(context, "up", service=service)


@task(help={"service": "If specified, only affect this service."})
def start(context, service=None, use_hosted_dolt=False):
    """Start Nautobot and its dependencies in detached mode."""
    print("Starting Nautobot in detached mode...")
    docker_compose(context, "up --detach", service=service, use_hosted_dolt=use_hosted_dolt)


@task
def restart(context):
    """Gracefully restart all containers."""
    print("Restarting Nautobot...")
    docker_compose(context, "restart")


@task
def stop(context, use_hosted_dolt=False):
    """Stop Nautobot and its dependencies."""
    print("Stopping Nautobot...")
    docker_compose(context, "down", use_hosted_dolt=use_hosted_dolt)


@task
def destroy(context, use_hosted_dolt=False):
    """Destroy all containers and volumes."""
    print("Destroying Nautobot...")
    docker_compose(context, "down --volumes --remove-orphans", use_hosted_dolt=use_hosted_dolt)


@task
def vscode(context):
    """Launch Visual Studio Code with the appropriate Environment variables to run in a container."""
    command = "code nautobot.code-workspace"

    context.run(command)


@task(
    help={
        "service": "Docker-compose service name to view (default: nautobot)",
        "follow": "Follow logs",
        "tail": "Tail N number of lines or 'all'",
    }
)
def logs(context, service="nautobot", follow=False, tail=None):
    """View the logs of a docker-compose service."""
    command = "logs "

    if follow:
        command += "--follow "
    if tail:
        command += f"--tail={tail} "

    command += service
    docker_compose(context, command)


# ------------------------------------------------------------------------------
# ACTIONS
# ------------------------------------------------------------------------------
@task
def nbshell(context):
    """Launch an interactive nbshell session."""
    command = "nautobot-server nbshell"
    run_command(context, command)


@task
def shell_plus(context):
    """Launch an interactive shell_plus session."""
    command = "nautobot-server shell_plus"
    run_command(context, command)


@task
def cli(context):
    """Launch a bash shell inside the running Nautobot container."""
    run_command(context, "bash")


@task(
    help={
        "user": "name of the superuser to create (default: admin)",
    }
)
def createsuperuser(context, user="admin"):
    """Create a new Nautobot superuser account (default: "admin"), will prompt for password."""
    command = f"nautobot-server createsuperuser --username {user}"

    run_command(context, command)


@task(
    help={
        "name": "name of the migration to be created; if unspecified, will autogenerate a name",
    }
)
def makemigrations(context, name=""):
    """Perform makemigrations operation in Django."""
    command = "nautobot-server makemigrations nautobot_version_control"

    if name:
        command += f" --name {name}"

    run_command(context, command)


@task
def migrate(context, use_hosted_dolt=False):
    """Perform migrate operation in Django."""
    command = "nautobot-server migrate"

    run_command(context, command, use_hosted_dolt=use_hosted_dolt)

@task
def load_data(context, use_hosted_dolt=False):
    """Load data."""
    commands = [
        "nautobot-server cleanup_data",
        "nautobot-server loaddata development/db.json",
    ]
    for command in commands:
        compose_command = f"run --entrypoint '{command}' nautobot"
        docker_compose(context, compose_command, pty=True, use_hosted_dolt=use_hosted_dolt)

@task(help={})
def post_upgrade(context):
    """
    Performs Nautobot common post-upgrade operations using a single entrypoint.

    This will run the following management commands with default settings, in order:

    - migrate
    - trace_paths
    - collectstatic
    - remove_stale_contenttypes
    - clearsessions
    - invalidate all
    """
    command = "nautobot-server post_upgrade"

    run_command(context, command)


# ------------------------------------------------------------------------------
# DOCS
# ------------------------------------------------------------------------------
@task
def docs(context):
    """Build and serve docs locally for development."""
    command = "mkdocs serve -v"

    if is_truthy(context.nautobot_version_control.local):
        print(">>> Serving Documentation at http://localhost:8001")
        run_command(context, command)
    else:
        start(context, service="docs")


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------
@task(
    help={
        "autoformat": "Apply formatting recommendations automatically, rather than failing if formatting is incorrect.",
    }
)
def black(context, autoformat=False):
    """Check Python code style with Black."""
    if autoformat:
        black_command = "black"
    else:
        black_command = "black --check --diff"

    command = f"{black_command} ."

    run_command(context, command)


@task
def flake8(context):
    """Check for PEP8 compliance and other style issues."""
    command = "flake8 . --config .flake8"
    run_command(context, command)


@task
def hadolint(context):
    """Check Dockerfile for hadolint compliance and other style issues."""
    command = "hadolint development/Dockerfile"
    run_command(context, command)


@task
def pylint(context):
    """Run pylint code analysis."""
    command = 'pylint --init-hook "import nautobot; nautobot.setup()" --rcfile pyproject.toml nautobot_version_control'
    run_command(context, command)


@task
def pydocstyle(context):
    """Run pydocstyle to validate docstring formatting adheres to NTC defined standards."""
    # We exclude the /migrations/ directory since it is autogenerated code
    command = "pydocstyle ."
    run_command(context, command)


@task
def bandit(context):
    """Run bandit to validate basic static code security analysis."""
    command = "bandit --recursive . --configfile .bandit.yml"
    run_command(context, command)


@task
def yamllint(context):
    """Run yamllint to validate formating adheres to NTC defined YAML standards.

    Args:
        context (obj): Used to run specific commands
    """
    command = "yamllint . --format standard"
    run_command(context, command)


@task
def check_migrations(context):
    """Check for missing migrations."""
    command = "nautobot-server --config=nautobot/core/tests/nautobot_config.py makemigrations --dry-run --check"

    run_command(context, command)


@task(
    help={
        "keepdb": "save and re-use test database between test runs for faster re-testing.",
        "label": "specify a directory or module to test instead of running all Nautobot tests",
        "failfast": "fail as soon as a single test fails don't run the entire test suite",
        "buffer": "Discard output from passing tests",
    }
)
def unittest(context, keepdb=False, label="nautobot_version_control", failfast=False, buffer=True, verbose=True, debug=True, use_hosted_dolt=False):
    """Run Nautobot unit tests."""
    command = f"coverage run --module nautobot.core.cli test {label}"

    if keepdb:
        command += " --keepdb"
    if failfast:
        command += " --failfast"
    if buffer:
        command += " --buffer"
    if verbose:
        command += " --verbosity 2"
    if debug:
        command += " --debug-sql"
    run_command(context, command, use_hosted_dolt=use_hosted_dolt)


@task
def unittest_coverage(context):
    """Report on code test coverage as measured by 'invoke unittest'."""
    command = "coverage report --skip-covered --include 'nautobot_version_control/*' --omit *migrations*"

    run_command(context, command)


@task(
    help={
        "failfast": "fail as soon as a single test fails don't run the entire test suite",
    }
)
def tests(context, failfast=False):
    """Run all tests for this plugin."""
    # If we are not running locally, start the docker containers so we don't have to for each test
    if not is_truthy(context.nautobot_version_control.local):
        print("Starting Docker Containers...")
        start(context)
    # Sorted loosely from fastest to slowest
    print("Running black...")
    black(context)
    print("Running flake8...")
    flake8(context)
    print("Running bandit...")
    bandit(context)
    print("Running pydocstyle...")
    pydocstyle(context)
    print("Running yamllint...")
    yamllint(context)
    print("Running pylint...")
    pylint(context)
    print("Running unit tests...")
    unittest(context, failfast=failfast)
    print("All tests have passed!")
    unittest_coverage(context)

# ------------------------------------------------------------------------------
# Clean - these tasks are for running tests or starting services, and performs all
# the necessary steps to do so: destroy, build, migrate, etc.
# ------------------------------------------------------------------------------

def load_dotenv(path):
    env_vars = {}
    with open(path) as f:
        env_data = f.read().splitlines()
    for line in env_data:
        if "=" not in line:
            continue
        if line.startswith("#"):
            continue
        key, val = line.split("=", 1)
        os.environ[key] = val

def reset_hosted_db():
    load_dotenv(path="development/creds.env")

    dolt_host = os.getenv("NAUTOBOT_HOSTED_DB_HOST")
    if dolt_host is None:
        print("Error: NAUTOBOT_HOSTED_DB_HOST environment variable not set")
        return False
    dolt_user = os.getenv("NAUTOBOT_HOSTED_DB_USER")
    if dolt_user is None:
        print("Error: NAUTOBOT_HOSTED_DB_USER environment variable not set")
        return False
    dolt_password = os.getenv("NAUTOBOT_HOSTED_DB_PASSWORD")
    if dolt_password is None:
        print("Error: NAUTOBOT_HOSTED_DB_PASSWORD environment variable not set")
        return False

    now = time.localtime()
    time_stamp = time.strftime("%Y_%m_%d_%H_%M_%S", now)
    debug_db_name = f"test_nautobot_hosted_{time_stamp}"

    queries = [
        "DROP DATABASE IF EXISTS nautobot;",
        "CREATE DATABASE nautobot CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;",
        "DROP DATABASE IF EXISTS test_nautobot;",
        "CREATE DATABASE test_nautobot CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;",
        f"DROP DATABASE IF EXISTS {debug_db_name};",
        f"CREATE DATABASE {debug_db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;",
    ]
    for query in queries:
        command = [
                "mysql",
                "-h",
                dolt_host,
                "-u",
                dolt_user,
                "-p" + dolt_password,
                "-e",
                query,
            ]
        subprocess.run(
            command,
            check=True,
            # env=env,
        )
    return True

@task
def clean_tests(context, label="nautobot_version_control", use_hosted_dolt=False):
    """Run all tests for this plugin."""
    if use_hosted_dolt:
        print("Running tests with hosted dolt database.")
    else:
        print("Running tests with local dolt database.")

    if use_hosted_dolt:
        if not reset_hosted_db():
            print("Failed to reset hosted database.")
            return

    destroy(context)
    build(context, use_hosted_dolt=use_hosted_dolt)
    unittest(context, keepdb=True, use_hosted_dolt=use_hosted_dolt, label=label)

@task
def clean_start(context, use_hosted_dolt=False):
    """Start the docker containers."""
    if use_hosted_dolt:
        print("Starting nautobot and plugin with hosted dolt database.")
    else:
        print("Starting nautobot and plugin with local dolt database.")

    if use_hosted_dolt:
        if not reset_hosted_db():
            print("Failed to reset hosted database.")
            return

    stop(context, use_hosted_dolt=False)
    stop(context, use_hosted_dolt=True)

    destroy(context, use_hosted_dolt=False)
    destroy(context, use_hosted_dolt=True)

    build(context, use_hosted_dolt=use_hosted_dolt)
    migrate(context, use_hosted_dolt=use_hosted_dolt)
    load_data(context, use_hosted_dolt=use_hosted_dolt)
    start(context, use_hosted_dolt=use_hosted_dolt)

