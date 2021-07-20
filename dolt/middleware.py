from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.shortcuts import redirect
from django.utils.safestring import mark_safe

from dynamic_db_router import in_database

from nautobot.extras.models.change_logging import ObjectChange

from dolt.constants import (
    DOLT_BRANCH_KEYWORD,
    DOLT_DEFAULT_BRANCH,
)
from dolt.versioning import query_on_branch
from dolt.models import Branch, Commit


def branch_from_request(request):
    if DOLT_BRANCH_KEYWORD in request.session:
        return request.session.get(DOLT_BRANCH_KEYWORD)
    if DOLT_BRANCH_KEYWORD in request.headers:
        return request.headers.get(DOLT_BRANCH_KEYWORD)
    return DOLT_DEFAULT_BRANCH


class DoltBranchMiddleware:
    # DOLT_BRANCH_KEYWORD = "branch"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # lookup the active branch in the session cookie
        requested = branch_from_request(request)
        with query_on_branch(DOLT_DEFAULT_BRANCH):
            try:
                branch = Branch.objects.get(pk=requested)
            except ObjectDoesNotExist:
                messages.warning(
                    request,
                    mark_safe(
                        f"""<div class="text-center">branch not found: {requested}</div>"""
                    ),
                )
                request.session[DOLT_BRANCH_KEYWORD] = DOLT_DEFAULT_BRANCH
                branch = Branch.objects.get(pk=DOLT_DEFAULT_BRANCH)
        with query_on_branch(branch):
            if request.user.is_authenticated:
                # inject the "active branch" banner
                msg = f"""
                    <div class="text-center">
                        Active Branch: {Branch.active_branch()}
                    </div>
                """
                messages.info(request, mark_safe(msg))
            return view_func(request, *view_args, **view_kwargs)


class DoltAutoCommitMiddleware(object):
    """
    adapted from nautobot.extras.middleware.ObjectChangeMiddleware
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request with auto-dolt-commit enabled
        branch = branch_from_request(request)
        with AutoDoltCommit(request, branch):
            return self.get_response(request)


class AutoDoltCommit(object):
    """
    adapted from `nautobot.extras.context_managers`
    """

    def __init__(self, request, branch):
        self.request = request
        self.branch = branch
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
        Commit(message=self._get_commit_message()).save(
            branch=self.branch,
            author=self.request.user,
        )

    def _get_commit_message(self):
        if not self.changes:
            return "auto dolt commit"
        self.changes = sorted(self.changes, key=lambda obj: obj.time)
        return "; ".join([str(c) for c in self.changes])
