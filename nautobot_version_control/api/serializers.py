"""serializers.py implements serializers for different modules."""
from rest_framework import serializers
from nautobot_version_control.models import Branch, Commit, PullRequest, PullRequestReview


class BranchSerializer(serializers.ModelSerializer):
    """BranchSerializer serializes a Branch"""

    class Meta:
        model = Branch
        fields = "__all__"


class CommitSerializer(serializers.ModelSerializer):
    """CommitSerializer serializes a Commit"""

    class Meta:
        model = Commit
        fields = "__all__"


class PullRequestSerializer(serializers.ModelSerializer):
    """PullRequestSerializer serializes a PullRequest"""

    class Meta:
        model = PullRequest
        fields = "__all__"


class PullRequestReviewSerializer(serializers.ModelSerializer):
    """PullRequestReviewSerializer serializes a PullRequestReview"""

    class Meta:
        model = PullRequestReview
        fields = "__all__"
