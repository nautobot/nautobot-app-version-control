from contextlib import contextmanager
from copy import deepcopy

from django.conf import settings
from django.db import connection, transaction
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


@contextmanager
def query_at_commit(commit):
    # TODO: use database revision syntax (when available)
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT @@{DB_NAME}_working;")
                previous = cursor.fetchone()[0]
                cursor.execute(f"SET @@{DB_NAME}_working = '{commit}';")

            yield

            with connection.cursor() as cursor:
                cursor.execute(f"SET @@{DB_NAME}_working = '{previous}';")

    except Exception as e:
        raise e


def change_branches(sess=None, branch=None):
    if sess is None or branch is None:
        raise ValueError("invalid args to change_branches()")
    sess[DOLT_BRANCH_KEYWORD] = branch
