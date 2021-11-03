"""serializers.py implements serializers for different modules."""
from nautobot.core.api import ValidatedModelSerializer
from dolt.models import Branch, Commit, PullRequest, PullRequestReview


class BranchSerializer(ValidatedModelSerializer):
    """BranchSerializer serializes a Branch"""

    class Meta:
        model = Branch
        fields = [
            "name",
            "hash",
            "latest_committer",
            "latest_committer_email",
            "latest_commit_date",
            "latest_commit_message",
        ]


class CommitSerializer(ValidatedModelSerializer):
    """CommitSerializer serializes a Commit"""

    class Meta:
        model = Commit
        fields = [
            "commit_hash",
            "committer",
            "email",
            "date",
            "message",
        ]


class PullRequestSerializer(ValidatedModelSerializer):
    """PullRequestSerializer serializes a PullRequest"""

    class Meta:
        model = PullRequest
        fields = [
            "title",
            "state",
            "source_branch",
            "destination_branch",
            "description",
            "creator",
            "created_at",
        ]


class PullRequestReviewSerializer(ValidatedModelSerializer):
    """PullRequestReviewSerializer serializes a PullRequestReview"""

    class Meta:
        model = PullRequestReview
        fields = ["pull_request", "reviewer", "reviewed_at", "state", "summary"]
