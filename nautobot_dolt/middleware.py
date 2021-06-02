import uuid

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.utils.safestring import mark_safe

from nautobot_dolt.constants import (
    DOLT_BRANCH_KEYWORD,
    DOLT_VERSIONED_URL_PREFIXES,
    DOLT_DEFAULT_BRANCH,
)
from nautobot_dolt.context_managers import AutoDoltCommit
from nautobot_dolt.models import Branch


class DoltBranchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # check for a `branch` query string param
        branch = request.GET.get(DOLT_BRANCH_KEYWORD, None)

        if branch:
            # update the session cookie with the active branch
            request.session[DOLT_BRANCH_KEYWORD] = branch
        elif self._is_vcs_route(request):
            # route is under version control, but no branch was specified,
            # lookup the active branch in the session cookie.
            branch = request.session.get(DOLT_BRANCH_KEYWORD, DOLT_DEFAULT_BRANCH)
            # provide the `branch` query string param and redirect
            return redirect(f"{request.path}?{DOLT_BRANCH_KEYWORD}={branch}")

        return self.get_response(request)

    @staticmethod
    def _is_vcs_route(request):
        """
        Determines whether the requested page is under version-control
        and needs to be redirected to read from a specific branch.
        """
        if request.GET.get(DOLT_BRANCH_KEYWORD, None):
            # if a branch is already specified in the
            # query string, don't redirect
            return False

        return (
            request.path.startswith(DOLT_VERSIONED_URL_PREFIXES) or request.path == "/"
        )

    def process_view(self, request, view_func, view_args, view_kwargs):
        # lookup the active branch in the session cookie
        branch = request.session.get(DOLT_BRANCH_KEYWORD, DOLT_DEFAULT_BRANCH)
        try:
            # switch the database to use the active branch
            Branch.objects.get(pk=branch).checkout_branch()
        except ObjectDoesNotExist:
            messages.warning(request, mark_safe(f"<h4>branch not found: {branch}</h4>"))
        # verify the active branch
        active = Branch.active_branch()
        # inject the "active branch" banner
        messages.info(request, mark_safe(f"<h4>active branch: {active}</h4>"))

        return view_func(request, *view_args, **view_kwargs)


class DoltAutoCommitMiddleware(object):
    """
    adapted from nautobot.extras.middleware.ObjectChangeMiddleware
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request with auto-dolt-commit enabled
        with AutoDoltCommit(request):
            response = self.get_response(request)

        return response
