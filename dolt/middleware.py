import uuid

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.utils.safestring import mark_safe

from dolt.constants import (
    DOLT_BRANCH_KEYWORD,
    DOLT_DEFAULT_BRANCH,
)
from dolt.context_managers import AutoDoltCommit
from dolt.models import Branch


class DoltBranchMiddleware:
    # DOLT_BRANCH_KEYWORD = "branch"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    @staticmethod
    def _requested_branch(request):
        if DOLT_BRANCH_KEYWORD in request.session:
            return request.session.get(DOLT_BRANCH_KEYWORD)
        if DOLT_BRANCH_KEYWORD in request.headers:
            return request.headers.get(DOLT_BRANCH_KEYWORD)
        return DOLT_DEFAULT_BRANCH

    def process_view(self, request, view_func, view_args, view_kwargs):
        # lookup the active branch in the session cookie
        branch = self._requested_branch(request)
        try:
            # switch the database to use the active branch
            Branch.objects.get(pk=branch).checkout_branch()
        except ObjectDoesNotExist:
            messages.warning(
                request,
                mark_safe(
                    f"""<div class="text-center">branch not found: {branch}</div>"""
                ),
            )
        # inject the "active branch" banner
        active = Branch.active_branch()
        messages.info(
            request,
            mark_safe(f"""<div class="text-center">Active Branch: {active}</div>"""),
        )

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
