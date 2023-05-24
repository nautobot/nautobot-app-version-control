"""Django views for Nautobot Version Control."""

from rest_framework.routers import APIRootView
from nautobot.extras.api.views import CustomFieldModelViewSet

from nautobot_version_control import filters
from nautobot_version_control.models import Branch, Commit, PullRequest, PullRequestReview

from . import serializers


class VCSRootView(APIRootView):
    """VCS API root view."""

    def get_view_name(self):
        """Returns the name of the view."""
        return "VCS"


#
# Branches
#


class BranchViewSet(CustomFieldModelViewSet):  # pylint: disable=too-many-ancestors
    """BranchViewSet render a view for the Branch model."""

    queryset = Branch.objects.all()
    serializer_class = serializers.BranchSerializer
    filterset_class = filters.BranchFilterSet


#
# Commits
#


class CommitViewSet(CustomFieldModelViewSet):  # pylint: disable=too-many-ancestors
    """CommitViewSet render a view for the Commit model."""

    queryset = Commit.objects.all()
    serializer_class = serializers.CommitSerializer
    filterset_class = filters.CommitFilterSet


#
# Pull Requests
#


class PullRequestViewSet(CustomFieldModelViewSet):  # pylint: disable=too-many-ancestors
    """PullRequestViewSet render a view for the PullRequest model."""

    queryset = PullRequest.objects.all()
    serializer_class = serializers.PullRequestSerializer
    filterset_class = filters.PullRequestFilterSet


#
# Pull Request Reviews
#


class PullRequestReviewViewSet(CustomFieldModelViewSet):  # pylint: disable=too-many-ancestors
    """PullRequestReviewViewSet render a view for the PullRequestReviewV model."""

    queryset = PullRequestReview.objects.all()
    serializer_class = serializers.PullRequestReviewSerializer
    filterset_class = filters.PullRequestReviewFilterSet
