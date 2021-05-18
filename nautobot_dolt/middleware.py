from django.shortcuts import redirect

from nautobot_dolt.constants import (
    DOLT_BRANCH_KEYWORD,
    DOLT_VERSIONED_URL_PREFIXES,
    DOLT_DEFAULT_BRANCH,
)
from nautobot_dolt.models import Branch


class DoltMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._redirect_needed(request):
            branch = request.session.get(DOLT_BRANCH_KEYWORD, DOLT_DEFAULT_BRANCH)
            return redirect(f"{request.path}?{DOLT_BRANCH_KEYWORD}={branch}")

        return self.get_response(request)

    @staticmethod
    def _redirect_needed(request):
        """
        Versioned domain pages will be redirected if they
        do not contain a `dolt_branch` query string param.
        """
        if request.GET.get(DOLT_BRANCH_KEYWORD, None):
            return False

        # query string param not found
        return (
            request.path.startswith(DOLT_VERSIONED_URL_PREFIXES) or request.path == "/"
        )  # home page

    def process_view(self, request, view_func, view_args, view_kwargs):
        branch = request.GET.get(DOLT_BRANCH_KEYWORD, None)
        if branch:
            request.session[DOLT_BRANCH_KEYWORD] = branch
            Branch.objects.get(pk=branch).checkout_branch()
        return view_func(request, *view_args, **view_kwargs)
