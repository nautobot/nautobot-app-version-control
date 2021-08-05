from contextlib import contextmanager
from copy import deepcopy
import uuid

from django.conf import settings
from django.db import connection, connections, transaction
from django.db.models.signals import m2m_changed, pre_delete, post_save

from nautobot.extras.models.change_logging import ObjectChange

from dolt.constants import DB_NAME, DOLT_BRANCH_KEYWORD
from dolt.models import Branch


@contextmanager
def query_on_branch(branch):
    with connection.cursor() as cursor:
        prev = str(Branch.active_branch())
        cursor.execute(f"""SELECT dolt_checkout("{branch}") FROM dual;""")
        yield
        cursor.execute(f"""SELECT dolt_checkout("{prev}") FROM dual;""")


def change_branches(sess=None, branch=None):
    if sess is None or branch is None:
        raise ValueError("invalid args to change_branches()")
    sess[DOLT_BRANCH_KEYWORD] = branch


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
