from contextlib import contextmanager
from copy import deepcopy

from django.conf import settings
from django.db import connection, transaction
from django.db.models.signals import m2m_changed, pre_delete, post_save

from dynamic_db_router.router import in_database

from nautobot.extras.models.change_logging import ObjectChange

from dolt.constants import DB_NAME


@contextmanager
def query_on_branch(branch):
    with in_database(db_from_revision(branch), read=True, write=True):
        yield


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


def db_from_revision(branch):
    db = deepcopy(settings.DATABASES["default"])
    # set versioned database
    db["NAME"] = f"{DB_NAME}/{branch}"
    return db
