from contextlib import contextmanager
from copy import deepcopy

from django.contrib.contenttypes.models import ContentType
from django.db import connection, connections

from dolt.constants import DB_NAME, DOLT_BRANCH_KEYWORD


class DoltError(Exception):
    pass


def author_from_user(usr):
    if usr and usr.username and usr.email:
        return f"{usr.username} <{usr.email}>"
    # default to generic user
    return "nautobot <nautobot@ntc.com>"


def is_dolt_model(model):
    """
    Returns `True` if `instance` is an instance of
    a model from the Dolt plugin. Generally,
    """
    app_label = model._meta.app_label
    return app_label == "dolt"


def alter_session_branch(sess=None, branch=None):
    if sess is None or branch is None:
        raise ValueError("invalid args to change_branches()")
    sess[DOLT_BRANCH_KEYWORD] = branch


def active_branch():
    with connection.cursor() as cursor:
        cursor.execute("SELECT active_branch() FROM dual;")
        return cursor.fetchone()[0]


def db_for_commit(commit):
    """
    Uses "database-revision" syntax
    adds a database entry for the commit
    e.g. "nautobot/3a5mqdgao8029bf8ji0huobbskq1n1l5"
    TODO: add detail
    """
    cm_hash = str(commit)
    db = deepcopy(connections.databases["default"])
    db["id"] = cm_hash
    db["NAME"] = f"{DB_NAME}/{cm_hash}"
    connections.databases[cm_hash] = db
    return cm_hash


@contextmanager
def query_on_branch(branch):
    # TODO: remove in favor of db_for_commit
    with connection.cursor() as cursor:
        prev = active_branch()
        cursor.execute(f"""SELECT dolt_checkout("{branch}") FROM dual;""")
        yield
        cursor.execute(f"""SELECT dolt_checkout("{prev}") FROM dual;""")
