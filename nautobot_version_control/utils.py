"""Utility methods used throughout the plugin."""


from contextlib import contextmanager
from copy import deepcopy

from django.db import connection, connections

from nautobot_version_control.constants import DB_NAME, DOLT_BRANCH_KEYWORD


class DoltError(Exception):
    """DoltError is a type of error to represent errors from the Dolt database custom functions."""

    pass  # pylint: disable=W0107


def author_from_user(user):
    """Returns an author string from a user object.

    Note that while user.email is optional in Django, it's mandatory for Dolt.
    """
    if user:
        if user.email:
            return f"{user.username} <{user.email}>"
        # RFC 6761 defines .invalid as a reserved TLD that will never be used for real-world domains
        return f"{user.username} <{user.username}@nautobot.invalid>"
    # default to generic user
    return "unknown <unknown@nautobot.invalid>"


def is_dolt_model(model):
    """Returns `True` if `instance` is an instance of a model from the Dolt plugin."""
    app_label = model._meta.app_label
    return app_label == "nautobot_version_control"


def alter_session_branch(sess=None, branch=None):
    """Set the session cook branch to a new branch."""
    if sess is None or branch is None:
        raise ValueError("invalid args to change_branches()")
    sess[DOLT_BRANCH_KEYWORD] = branch


def active_branch():
    """Returns the current active_branch from dolt."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT active_branch();")
        return cursor.fetchone()[0]


def db_for_commit(commit):
    """Uses "database-revision" syntax adds a database entry for the commit e.g. "nautobot/3a5mqdgao8029bf8ji0huobbskq1n1l5"."""
    cm_hash = str(commit)
    if len(cm_hash) != 32:
        raise Exception("commit hash length is incorrect")
    database = deepcopy(connections.databases["default"])
    database["id"] = cm_hash
    database["NAME"] = f"{DB_NAME}/{cm_hash}"
    connections.databases[cm_hash] = database
    return cm_hash


@contextmanager
def query_on_branch(branch):
    """Checkout to another branch, runs a query, and checkouts back to main."""
    # TODO: remove in favor of db_for_commit
    with connection.cursor() as cursor:
        prev = active_branch()
        cursor.execute(f"""CALL dolt_checkout("{branch}");""")  # TODO: not safe
        yield
        cursor.execute(f"""CALL dolt_checkout("{prev}");""")  # TODO: not safe
