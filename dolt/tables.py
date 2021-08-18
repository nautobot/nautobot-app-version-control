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

__all__ = ("BranchTable", "ConflictsSummaryTable", "CommitTable", "PullRequestTable")


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


class ConflictsSummaryTable(BaseTable):
    """
    Summary table for `Conflicts` and `ConstraintViolations`
    """

    class Meta(BaseTable.Meta):
        model = Conflicts
        fields = ("table", "num_conflicts", "num_violations")
        default_columns = fields


CONFLICT_TABLE_JSON = """
{% load helpers %}
<div class="rendered-json-data">
    <pre>{{ record.conflicts|render_yaml }}</pre>
</div>
"""


class ConflictsTable(BaseTable):
    conflicts = tables.TemplateColumn(
        template_code=CONFLICT_TABLE_JSON,
        verbose_name="Conflicts",
    )

    class Meta(BaseTable.Meta):
        model = Conflicts
        fields = (
            "table",
            "id",
            "conflicts",
        )
        default_columns = fields


class ConstraintViolationsTable(BaseTable):
    class Meta(BaseTable.Meta):
        model = Conflicts
        fields = (
            "table",
            "id",
            "violation_type",
            "violations",
        )
        default_columns = fields


#
# PullRequest
#

PR_STATUS_BADGES = """
<div>
{% if record.status == "open" %}
    <span class="label label-primary">Open</span>
{% elif record.status == "in-review" %}
    <span class="label label-primary">In Review</span>
{% elif record.status == "blocked" %}
    <span class="label label-warning">Blocked</span>
{% elif record.status == "approved" %}
    <span class="label label-success">Approved</span>
{% elif record.status == "merged" %}
    <span class="label label-info">Merged</span>
{% elif record.status == "closed" %}
    <span class="label label-danger">Closed</span>
{% else %}
    <span> - </span>
{% endif %}
</div>
"""


class PullRequestTable(BaseTable):
    pk = ToggleColumn()
    status = tables.TemplateColumn(
        template_code=PR_STATUS_BADGES,
        verbose_name="Status",
    )
    title = tables.LinkColumn()

    class Meta(BaseTable.Meta):
        model = PullRequest
        fields = (
            "pk",
            "title",
            "status",
            "source_branch",
            "destination_branch",
            "description",
            "creator",
            "created_at",
        )
        default_columns = fields
