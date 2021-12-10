"""routers.py manages the GlobalStateRouter."""

from django.utils.safestring import mark_safe
from nautobot_version_control.constants import DOLT_DEFAULT_BRANCH, GLOBAL_DB
from nautobot_version_control.utils import DoltError, is_dolt_model, active_branch

from . import is_global_router_enabled, is_versioned_model


class GlobalStateRouter:
    """GlobalStateRouter manages the correct db to write either branch specific state or global state."""

    global_db = GLOBAL_DB

    def db_for_read(self, model, **hints):  # pylint: disable=W0613
        """
        Directs read queries to the global state db for non-versioned models.
        Versioned models use the 'default' database and the Dolt branch that
        was checked out in `DoltBranchMiddleware`.
        """
        if not is_global_router_enabled():
            return None

        if is_versioned_model(model):
            return None

        return self.global_db

    def db_for_write(self, model, **hints):  # pylint: disable=W0613
        """
        Directs write queries to the global state db for non-versioned models.
        Versioned models use the 'default' database and the Dolt branch that
        was checked out in `DoltBranchMiddleware`.
        Prevents writes of non-versioned models on non-primary branches.
        """
        if not is_global_router_enabled():
            return None

        if is_dolt_model(model):
            # Dolt models can be created or edited from any branch.
            # Edits will be applied to the "main"
            return self.global_db

        if is_versioned_model(model):
            return None

        if self.branch_is_not_primary():
            # non-versioned models can only be edited on "main"
            raise DoltError(
                mark_safe(
                    f"""Error writing model <strong>{model.__name__}</strong>
                        on branch <strong>"{active_branch()}"</strong>:
                        non-versioned models must be written on branch
                        <strong>"{DOLT_DEFAULT_BRANCH}"</strong>."""
                )
            )

        return self.global_db

    def allow_relation(self, obj1, obj2, **hints):  # pylint: disable=W0613.R0201
        """allow_relation allows a relation between obj1 and obj2 too exist."""
        return True

    @staticmethod
    def branch_is_not_primary():
        """branch_is_not_primary returns whether the active_branch is the default branch."""
        return active_branch() != DOLT_DEFAULT_BRANCH
