"""serializers.py implements serializers for different modules."""
from nautobot.core.api import ValidatedModelSerializer
from nautobot_version_control.models import Branch, Commit, PullRequest, PullRequestReview


class BranchSerializer(ValidatedModelSerializer):
    """BranchSerializer serializes a Branch"""

    class Meta:
        model = Branch
        fields = "__all__"


class CommitSerializer(ValidatedModelSerializer):
    """CommitSerializer serializes a Commit"""

    class Meta:
        model = Commit
        fields = "__all__"


class PullRequestSerializer(ValidatedModelSerializer):
    """PullRequestSerializer serializes a PullRequest"""

    class Meta:
        model = PullRequest
        fields = "__all__"


class PullRequestReviewSerializer(ValidatedModelSerializer):
    """PullRequestReviewSerializer serializes a PullRequestReview"""

    class Meta:
        model = PullRequestReview
        fields = "__all__"
