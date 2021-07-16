from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.db import SessionStore
from django.db import connections

from dynamic_db_router.router import DynamicDbRouter, THREAD_LOCAL

from . import is_versioned_model
from dolt.constants import DB_NAME, DOLT_DEFAULT_BRANCH


class AuthPermissionsRouter(object):
    """
    TODO
    """

    route_app_labels = ("auth",)

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return "auth_db"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return "auth_db"
        return None


class ModelVersionRouter(DynamicDbRouter):
    """
    TODO
    """

    # TODO: get from settings?
    static_dbs = ("auth_db", "default")
    primary_branch_db = "nautobot/master"

    def db_for_read(self, model, **hints):
        """
        Directs read queries to the versioned db for versioned models.
        Makes no db suggestion for non-versioned models.
        """
        if is_versioned_model(model):
            return super().db_for_read(model)
        return None

    def db_for_write(self, model, **hints):
        """
        Directs read queries to the versioned db for versioned models.
        Prevents writes of non-versioned models to non-primary branches.
        """
        if is_versioned_model(model):
            return super().db_for_write(model)
        if self._versioned_db_requested():
            raise ValueError("cannot write non-version model on non-primary branch")
        return None

    def _versioned_db_requested(self):
        """
        Introspects the `THREAD_LOCAL` object used by the parent class `DynamicDbRouter`.
        `THREAD_LOCAL` will contain a `DB_FOR_WRITE_OVERRIDE` var if the current query
        is being executed inside an database versioning context manager (see versioning.py).
        If this is the case, we return true if non-primary-branch database is requested.
        """
        override = getattr(THREAD_LOCAL, "DB_FOR_WRITE_OVERRIDE", [None])[-1]
        if not override or override in self.static_dbs:
            # query executed outside of versioned context manager
            return False

        override_db_name = connections[override].settings_dict["NAME"]
        if override_db_name == self.primary_branch_db:
            return False
        return True
