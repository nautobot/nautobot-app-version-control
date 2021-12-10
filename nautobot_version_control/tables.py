"""tables.py contains modules for implementing view tables for different models."""

import django_tables2 as tables
from django_tables2 import A
from nautobot.utilities.tables import BaseTable, ToggleColumn, ButtonsColumn

from nautobot_version_control.models import (
    Branch,
    Conflicts,
    Commit,
    PullRequest,
)

__all__ = ("BranchTable", "ConflictsSummaryTable", "CommitTable", "PullRequestTable")


#
# Branches
#

BRANCH_TABLE_BADGES = """
<div>
   {% if not record.active %}
        <a href="{% url 'plugins:nautobot_version_control:branch_checkout' pk=record.pk %}" class="btn btn-xs btn-primary" title="activate">
            Activate
        </a>
   {% endif %}
    <a href="{% url 'plugins:nautobot_version_control:pull_request_add' %}?source_branch={{ record.pk }}" class="btn btn-xs btn-success" title="pull_request">
        Pull Request
    </a>
    <a href="{% url 'plugins:nautobot_version_control:pull_request_add' %}?source_branch={{ default_branch }}&destination_branch={{ record.pk }}" class="btn btn-xs btn-warning" title="catch_up">
        Catchup
    </a>
</div>
"""


ACTIVE_BRANCH_BADGE = """
{% if record.active %}
    <div class="btn btn-xs btn-success" title="active">
        Active
    </div>
{% endif %}
"""


class BranchTable(BaseTable):
    """BranchTable render the table in the branch_list view."""

    pk = ToggleColumn()
    name = tables.LinkColumn()
    status = tables.TemplateColumn(ACTIVE_BRANCH_BADGE)
    hash = tables.LinkColumn("plugins:nautobot_version_control:commit", args=[A("hash")])
    actions = ButtonsColumn(
        Branch,
        pk_field="name",
        buttons=("checkout",),
        prepend_template=BRANCH_TABLE_BADGES,
    )
    ahead_behind = tables.Column(accessor=A("ahead_behind"), verbose_name="Ahead / Behind")
    starting_branch = tables.Column(accessor=A("source_branch"), verbose_name="Starting Branch")

    class Meta(BaseTable.Meta):
        model = Branch
        fields = (
            "pk",
            "name",
            "hash",
            "status",
            "ahead_behind",
            "created_by",
            "latest_committer",
            "latest_commit_date",
            "latest_commit_message",
            "starting_branch",
            "actions",
        )
        default_columns = (
            "name",
            "status",
            "ahead_behind",
            "created_by",
            "latest_committer",
            "latest_commit_date",
            "starting_branch",
            "actions",
        )


#
# Commits
#


class CommitTable(BaseTable):
    """CommitTable renders the commit table in the commit list view."""

    pk = ToggleColumn(visible=True)
    short_message = tables.LinkColumn(verbose_name="Commit Message")

    class Meta(BaseTable.Meta):
        model = Commit
        fields = (
            "pk",
            "short_message",
            "date",
            "committer",
            "email",
            "commit_hash",
        )
        default_columns = fields


class CommitRevertTable(BaseTable):
    """CommitRevert renders the commit revert table for the commit review view."""

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
    """Summary table for `Conflicts` and `ConstraintViolations`."""

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
    """ConflictsTable renders the table in the conflict list view."""

    conflicts = tables.TemplateColumn(
        template_code=CONFLICT_TABLE_JSON,
        verbose_name="Conflicts",
    )

    class Meta(BaseTable.Meta):
        model = Conflicts
        fields = (
            "model",
            "id",
            "conflicts",
        )
        default_columns = fields


class ConstraintViolationsTable(BaseTable):
    """ConstraintViolations renders the table in the constraint violations table."""

    class Meta(BaseTable.Meta):
        model = Conflicts
        fields = (
            "model",
            "id",
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
    """PullRequestTable renders the table in the pull request view."""

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
            "creator",
            "created_at",
        )
        default_columns = fields
