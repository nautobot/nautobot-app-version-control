"""views.py implements views for the api."""

from rest_framework.routers import APIRootView
from nautobot.extras.api.views import CustomFieldModelViewSet

from nautobot_version_control import filters
from nautobot_version_control.models import Branch, Commit, PullRequest, PullRequestReview

from . import serializers


class VCSRootView(APIRootView):
    """VCS API root view."""

    def get_view_name(self):
        """returns the name of the view."""
        return "VCS"


#
# Branches
#


class BranchViewSet(CustomFieldModelViewSet):
    """BranchViewSet render a view for the Branch model."""

    queryset = Branch.objects.all()
    serializer_class = serializers.BranchSerializer
    filterset_class = filters.BranchFilterSet


#
# Commits
#


class CommitViewSet(CustomFieldModelViewSet):
    """CommitViewSet render a view for the Commit model."""

    queryset = Commit.objects.all()
    serializer_class = serializers.CommitSerializer
    filterset_class = filters.CommitFilterSet


#
# Pull Requests
#


class PullRequestViewSet(CustomFieldModelViewSet):
    """PullRequestViewSet render a view for the PullRequest model."""

    queryset = PullRequest.objects.all()
    serializer_class = serializers.PullRequestSerializer
    filterset_class = filters.PullRequestFilterSet


#
# Pull Request Reviews
#


class PullRequestReviewViewSet(CustomFieldModelViewSet):
    """PullRequestReviewViewSet render a view for the PullRequestReviewV model."""

    queryset = PullRequestReview.objects.all()
    serializer_class = serializers.PullRequestReviewSerializer
    filterset_class = filters.PullRequestReviewFilterSet
