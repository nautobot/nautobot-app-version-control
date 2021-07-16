from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.db import SessionStore
from django.db import connections

from dynamic_db_router.router import DynamicDbRouter, THREAD_LOCAL

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

    whitelist = settings.MODEL_VERSION_WHITELIST
    # TODO: get from settings?
    static_dbs = ("auth_db", "default")
    primary_branch_db = "nautobot/master"

    def db_for_read(self, model, **hints):
        """
        Directs read queries to the versioned db for versioned models.
        Makes no db suggestion for non-versioned models.
        """
        if self._is_versioned_model(model):
            return super().db_for_read(model)
        return None

    def db_for_write(self, model, **hints):
        """
        Directs read queries to the versioned db for versioned models.
        Prevents writes of non-versioned models to non-primary branches.
        """
        if self._is_versioned_model(model):
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

    def _is_versioned_model(self, model):
        """
        Determines whether a model's content type is on the whitelist.
        The whilelist has the following layout:
            MODEL_VERSION_WHITELIST = {
                "dcim": True,
                "circuits": True,
                ...
                "extras": {
                    "computedfield": True,
                    "configcontext": True,
                    ...
                }
            },
        The top-level dict keys are app_labels. If the top-level dict value
        is `True`, then all models under that app_label are whitelisted.
        The top-level value may also be a nest dict containing a subset of
        whitelisted models within the app_label.
        """
        lbl = model._meta.app_label
        mdl = model.__name__.lower()

        if lbl not in self.whitelist:
            return False
        if isinstance(self.whitelist[lbl], bool):
            return self.whitelist[lbl]

        # subset specified
        if isinstance(self.whitelist[lbl], dict):
            if mdl not in self.whitelist[lbl]:
                return False
            if isinstance(self.whitelist[lbl][mdl], bool):
                return self.whitelist[lbl][mdl]

        raise ValueError("invalid model version whitelist")
