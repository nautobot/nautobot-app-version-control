"""
middleware.py contains the middleware add-ons needed for the dolt plugin to work.
"""

import random

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.safestring import mark_safe

from nautobot.extras.models.change_logging import ObjectChange

from dolt.constants import (
    DOLT_BRANCH_KEYWORD,
    DOLT_DEFAULT_BRANCH,
)
from dolt.models import Branch, Commit
from dolt.utils import DoltError, active_branch


def dolt_health_check_intercept_middleware(get_response):
    """
    Intercept health check calls and disregard
    TODO: fix health-check and remove
    """

    def middleware(request):
        if "/health" in request.path:
            return HttpResponse(status=201)
        return get_response(request)

    return middleware


class DoltBranchMiddleware:
    """ DoltBranchMiddleware keeps track of which branch the dolt database is on """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):  # pylint: disable=R0201
        """
        process_view maintains the dolt branch session cookie and verifies authentication. It then returns the
        view that needs to be rendered.
        """
        # Check whether the desired branch was passed in as a querystring
        query_string_branch = request.GET.get(DOLT_BRANCH_KEYWORD, None)
        if query_string_branch is not None:
            # update the session Cookie
            request.session[DOLT_BRANCH_KEYWORD] = query_string_branch
            return redirect(request.path)

        branch = DoltBranchMiddleware.get_branch(request)
        try:
            branch.checkout()
        except Exception as e:
            msg = f"could not checkout branch {branch}: {str(e)}"
            messages.error(request, mark_safe(msg))

        if request.user.is_authenticated:
            # Inject the "active branch" banner. Use a random number for the button id to ensure button listeners do not
            # clash. This is safe since it is JS generated on our end and should not be modifiable by any XSS attack.
            msg = DoltBranchMiddleware.get_active_branch_banner(
                random.randint(0, 10000)  # nosec random is not being used for security purposes.
            )
            messages.info(request, mark_safe(msg))

        try:
            return view_func(request, *view_args, **view_kwargs)
        except DoltError as e:
            messages.error(request, mark_safe(e))
            return redirect(request.path)

    @staticmethod
    def get_branch(request):
        """ get_branch returns the Branch object of the branch stored in the session cookie """
        # lookup the active branch in the session cookie
        requested = branch_from_request(request)
        try:
            return Branch.objects.get(pk=requested)
        except ObjectDoesNotExist:
            messages.warning(
                request,
                mark_safe(f"""<div class="text-center">branch not found: {requested}</div>"""),  # nosec
            )
            request.session[DOLT_BRANCH_KEYWORD] = DOLT_DEFAULT_BRANCH
            return Branch.objects.get(pk=DOLT_DEFAULT_BRANCH)

    @staticmethod
    def get_active_branch_banner(b_id):
        """ get_active_branch_banner returns a banner that renders the active branch and its share button """
        return f"""
                    <div class="text-center">
                        Active Branch: {active_branch()}
                        <div class = "pull-right">
                            <div class="btn btn-xs btn-primary" id="share-button-{b_id}">
                                Share
                            </div>
                        </div>
                    </div>
                    <script> 
                        const btn{b_id} = document.getElementById("share-button-{b_id}");
                        btn{b_id}.addEventListener('click', ()=>{{
                            const currLink = window.location.href;
                            const copiedLink = currLink + "?{DOLT_BRANCH_KEYWORD}={active_branch()}";
                            navigator.clipboard.writeText(copiedLink);
                            btn{b_id}.textContent = "Copied!"
                        }});
                    </script>
                """


class DoltAutoCommitMiddleware:
    """
    DoltAutoCommitMiddleware calls the AutoDoltCommit class on a request.
    - adapted from nautobot.extras.middleware.ObjectChangeMiddleware
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request with auto-dolt-commit enabled
        with AutoDoltCommit(request):
            return self.get_response(request)


class AutoDoltCommit:
    """
    AutoDoltCommit handles automatic dolt commits on the case than objects is created or deleted.
    - adapted from `nautobot.extras.context_managers`
    """

    def __init__(self, request):
        self.request = request
        self.commit = False
        self.changes_for_db = {}

    def __enter__(self):
        # Connect our receivers to the post_save and post_delete signals.
        post_save.connect(self._handle_update, dispatch_uid="dolt_commit_update")
        m2m_changed.connect(self._handle_update, dispatch_uid="dolt_commit_update")
        pre_delete.connect(self._handle_delete, dispatch_uid="dolt_commit_delete")

    def __exit__(self, type, value, traceback):  # pylint: disable=W0622
        if self.commit:
            self.make_commits()

        # Disconnect change logging signals. This is necessary to avoid recording any errant
        # changes during test cleanup.
        post_save.disconnect(self._handle_update, dispatch_uid="dolt_commit_update")
        m2m_changed.disconnect(self._handle_update, dispatch_uid="dolt_commit_update")
        pre_delete.disconnect(self._handle_delete, dispatch_uid="dolt_commit_delete")

    def _handle_update(self, sender, instance, **kwargs):  # pylint: disable=W0613
        """ Fires when an object is created or updated. """
        if isinstance(instance, ObjectChange):
            # ignore ObjectChange instances
            return

        msg = self.change_msg_for_update(instance, kwargs)
        self.collect_change(instance, msg)
        self.commit = True

    def _handle_delete(self, sender, instance, **kwargs):  # pylint: disable=W0613
        """ Fires when an object is deleted. """
        if isinstance(instance, ObjectChange):
            # ignore ObjectChange instances
            return

        msg = self.change_msg_for_delete(instance)
        self.collect_change(instance, msg)
        self.commit = True

    def make_commits(self):
        """ make_commits creates and saves a Commit object """
        for db, msgs in self.changes_for_db.items():
            msg = "; ".join(msgs)
            Commit(message=msg).save(
                user=self.request.user,
                using=db,
            )

    def collect_change(self, instance, msg):
        """ collect_change stores changes messages for each db """
        db = self.database_from_instance(instance)
        if db not in self.changes_for_db:
            self.changes_for_db[db] = []
        self.changes_for_db[db].append(msg)

    @staticmethod
    def database_from_instance(instance):
        """ database_from_instance returns a database from an instance type """
        return instance._state.db  # pylint: disable=W0212

    @staticmethod
    def change_msg_for_update(instance, kwargs):
        """ Generates a commit message for create or update. """
        created = "created" in kwargs and kwargs["created"]
        verb = "Created" if created else "Updated"
        return f"""{verb} {instance._meta.verbose_name} "{instance}" """

    @staticmethod
    def change_msg_for_delete(instance):
        """
        Generates a commit message for delete
        """
        return f"""Deleted {instance._meta.verbose_name} "{instance}" """


def branch_from_request(request):
    """
    Returns the active branch from a request
    :param request: A django request
    :return: Branch name
    """
    if DOLT_BRANCH_KEYWORD in request.session:
        return request.session.get(DOLT_BRANCH_KEYWORD)
    if DOLT_BRANCH_KEYWORD in request.headers:
        return request.headers.get(DOLT_BRANCH_KEYWORD)
    return DOLT_DEFAULT_BRANCH
