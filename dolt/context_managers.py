from datetime import datetime, timedelta
from contextlib import contextmanager
import pytz

from django.db import connection, transaction
from django.db.models.signals import m2m_changed, pre_delete, post_save

from nautobot.extras.models.change_logging import ObjectChange

from dolt.models import Commit, Branch


class AutoDoltCommit(object):
    """
    adapted from `nautobot.extras.context_managers`
    """

    def __init__(self, request):
        self.request = request
        self.commit = False
        self.changes = []

    def __enter__(self):
        # Connect our receivers to the post_save and post_delete signals.
        post_save.connect(self._handle_update, dispatch_uid="dolt_commit_update")
        m2m_changed.connect(self._handle_update, dispatch_uid="dolt_commit_update")
        pre_delete.connect(self._handle_delete, dispatch_uid="dolt_commit_delete")

    def __exit__(self, type, value, traceback):
        if self.commit:
            self._commit()

        # Disconnect change logging signals. This is necessary to avoid recording any errant
        # changes during test cleanup.
        post_save.disconnect(self._handle_update, dispatch_uid="dolt_commit_update")
        m2m_changed.disconnect(self._handle_update, dispatch_uid="dolt_commit_update")
        pre_delete.disconnect(self._handle_delete, dispatch_uid="dolt_commit_delete")

    def _handle_update(self, sender, instance, **kwargs):
        """
        Fires when an object is created or updated.
        """
        if type(instance) == ObjectChange:
            self.changes.append(instance)
        if "created" in kwargs:
            self.commit = True
        elif kwargs.get("action") in ["post_add", "post_remove"] and kwargs["pk_set"]:
            # m2m_changed with objects added or removed
            self.commit = True

    def _handle_delete(self, sender, instance, **kwargs):
        """
        Fires when an object is deleted.
        """
        self.commit = True

    def _commit(self):
        # todo: use ObjectChange to create commit message
        Commit(message=self._get_commit_message()).save(
            author=self._get_commit_author()
        )

    def _get_commit_message(self):
        if not self.changes:
            return "auto dolt commit"
        self.changes = sorted(self.changes, key=lambda obj: obj.time)
        return "; ".join([str(c) for c in self.changes])

    def _get_commit_author(self):
        usr = self.request.user
        if usr and usr.username and usr.email:
            return f"{usr.username} <{usr.email}>"
        return None


@contextmanager
def query_at_commit(commit):
    try:
        with transaction.atomic():
            active_branch = Branch.active_branch()
            with connection.cursor() as cursor:
                cursor.execute(f"SET @@nautobot_head = '{commit}';")

            yield

            with connection.cursor() as cursor:
                cursor.execute(f"SET @@nautobot_head = hashof('{active_branch}');")

    except Exception as e:
        raise e
