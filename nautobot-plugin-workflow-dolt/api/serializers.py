from nautobot.core.api import ValidatedModelSerializer
from nautobot.vcs.models import Branch, Commit


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
