import django_tables2 as tables
from django_tables2 import A

from nautobot_dolt.models import Branch, Commit
from nautobot.utilities.tables import BaseTable, ToggleColumn, ButtonsColumn

__all__ = (
    "BranchTable",
    "CommitTable",
)


#
# Branches
#

BRANCH_TABLE_BADGES = """
<div>
{% if record.active %}
    <div class="btn btn-xs btn-success" title="active">
        active
    </div>
{% else %}
    <a href="/?branch={{ record.name }}" class="btn btn-xs btn-primary" title="checkout">
        checkout
    </a>
{% endif %}
    <a href="{% url 'plugins:nautobot_dolt:branch_merge' src=record.pk %}" class="btn btn-xs btn-warning" title="merge">
        merge
    </a>
</div>
"""


class BranchTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    hash = tables.LinkColumn("plugins:nautobot_dolt:commit", args=[A("hash")])
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
        default_columns = ("active",) + fields


#
# Commits
#


class CommitTable(BaseTable):
    commit_hash = tables.LinkColumn()

    class Meta(BaseTable.Meta):
        model = Commit
        fields = (
            "commit_hash",
            "committer",
            "email",
            "date",
            "message",
        )
        default_columns = fields
