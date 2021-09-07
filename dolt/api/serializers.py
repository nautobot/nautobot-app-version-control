from nautobot.core.api import ValidatedModelSerializer
from dolt.models import Branch, Commit, PullRequest, PullRequestReview


class BranchSerializer(ValidatedModelSerializer):
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


class PullRequestCommentsSerializer(ValidatedModelSerializer):
    class Meta:
        model = PullRequestReview
        fields = ["pull_request", "reviewer", "reviewed_at", "state", "summary"]
