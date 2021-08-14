import django_tables2 as tables
from django_tables2 import A

from dolt.models import (
    Branch,
    Conflicts,
    ConstraintViolations,
    Commit,
    PullRequest,
    PullRequestReview,
)
from nautobot.utilities.tables import BaseTable, ToggleColumn, ButtonsColumn

__all__ = ("BranchTable", "ConflictsTable", "CommitTable", "PullRequestTable")


#
# Branches
#

BRANCH_TABLE_BADGES = """
<div>
{% if record.active %}
    <div class="btn btn-xs btn-success" title="active">
        Active
    </div>
{% endif %}
    <a href="{% url 'plugins:dolt:branch_checkout' pk=record.pk %}" class="btn btn-xs btn-primary" title="checkout">
        Checkout
    </a>
    <a href="{% url 'plugins:dolt:branch_merge' src=record.pk %}" class="btn btn-xs btn-warning" title="merge">
        Merge
    </a>
</div>
"""


class BranchTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    hash = tables.LinkColumn("plugins:dolt:commit", args=[A("hash")])
    actions = ButtonsColumn(
        Branch,
        pk_field="name",
        buttons=("checkout",),
        prepend_template=BRANCH_TABLE_BADGES,
    )

    class Meta(BaseTable.Meta):
        model = Branch
        fields = (
            "pk",
            "name",
            "hash",
            "latest_committer",
            "latest_committer_email",
            "latest_commit_date",
            "latest_commit_message",
            "actions",
        )
        default_columns = (
            "name",
            "latest_committer",
            "latest_committer_email",
            "latest_commit_date",
            "actions",
        )


#
# Commits
#


class CommitTable(BaseTable):
    short_message = tables.LinkColumn(verbose_name="Commit Message")

    class Meta(BaseTable.Meta):
        model = Commit
        fields = (
            "short_message",
            "date",
            "committer",
            "email",
            "commit_hash",
        )
        default_columns = fields


#
# Conflicts
#


class ConflictsTable(BaseTable):
    class Meta(BaseTable.Meta):
        model = Conflicts
        fields = (
            "table",
            "num_conflicts",
        )
        default_columns = fields


class ConstraintViolationsTable(BaseTable):
    class Meta(BaseTable.Meta):
        model = ConstraintViolations
        fields = (
            "table",
            "num_violations",
        )
        default_columns = fields


#
# PullRequest
#

PR_TABLE_BADGES = """
<div>
{% if record.state == 0 %}
    <span class="label label-success" title="active">
        Open
    </span>
{% elif record.state == 1 %}
    <span class="label label-info" title="merged">
        Merged
    </span>
{% elif record.state == 2 %}
    <span class="label label-danger" title="closed">
        Closed
    </span>
{% endif %}
</div>
"""


class PullRequestTable(BaseTable):
    pk = ToggleColumn()
    state = tables.TemplateColumn(
        template_code=PR_TABLE_BADGES,
        verbose_name="State",
    )
    title = tables.LinkColumn()

    class Meta(BaseTable.Meta):
        model = PullRequest
        fields = (
            "pk",
            "state",
            "title",
            "source_branch",
            "destination_branch",
            "description",
            "creator",
            "created_at",
        )
        default_columns = fields
