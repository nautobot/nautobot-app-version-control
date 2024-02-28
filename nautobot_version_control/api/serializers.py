"""Serializers for version_control app."""
from rest_framework import serializers
from nautobot_version_control.models import Branch, Commit, PullRequest, PullRequestReview


class BranchSerializer(serializers.ModelSerializer):
    """BranchSerializer serializes a Branch."""

    class Meta:
        """Set Meta Data for BranchSerializer, will serialize all fields."""

        model = Branch
        fields = "__all__"


class CommitSerializer(serializers.ModelSerializer):
    """CommitSerializer serializes a Commit."""

    class Meta:
        """Set Meta Data for CommitSerializer, will serialize all fields."""

        model = Commit
        fields = "__all__"


class PullRequestSerializer(serializers.ModelSerializer):
    """PullRequestSerializer serializes a PullRequest."""

    class Meta:
        """Set Meta Data for PullRequestSerializer, will serialize all fields."""

        model = PullRequest
        fields = "__all__"


class PullRequestReviewSerializer(serializers.ModelSerializer):
    """PullRequestReviewSerializer serializes a PullRequestReview."""

    class Meta:
        """Set Meta Data for PullRequestReviewSerializer, will serialize all fields."""

        model = PullRequestReview
        fields = "__all__"
