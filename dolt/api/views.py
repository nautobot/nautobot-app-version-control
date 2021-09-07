from rest_framework.routers import APIRootView
from dolt import filters
from nautobot.extras.api.views import CustomFieldModelViewSet, StatusViewSetMixin
from . import serializers
from dolt.models import Branch, Commit, PullRequest, PullRequestReview


class VCSRootView(APIRootView):
    """
    VCS API root view
    """

    def get_view_name(self):
        return "VCS"


#
# Branches
#


class BranchViewSet(CustomFieldModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = serializers.BranchSerializer
    filterset_class = filters.BranchFilterSet


#
# Commits
#


class CommitViewSet(CustomFieldModelViewSet):
    queryset = Commit.objects.all()
    serializer_class = serializers.CommitSerializer
    filterset_class = filters.CommitFilterSet


#
# Pull Requests
#


class PullRequestViewSet(CustomFieldModelViewSet):
    queryset = PullRequest.objects.all()
    serializer_class = serializers.PullRequestSerializer
    filterset_class = filters.PullRequestFilterSet


#
# Pull Request Comments
#


class PullRequestCommentsViewSet(CustomFieldModelViewSet):
    queryset = PullRequestReview.objects.filter(state=PullRequestReview.COMMENTED)
    serializer_class = serializers.PullRequestCommentsSerializer
    filterset_class = filters.PullRequestCommentFilterSet
