import django_tables2 as tables
from django_tables2 import A

from nautobot.dcim.tables import RegionTable, ManufacturerTable
from nautobot.vcs.contants import DOLT_BRANCH_KEYWORD
from nautobot.vcs.models import Branch, Commit
from nautobot.utilities.tables import BaseTable, ToggleColumn, ButtonsColumn

__all__ = (
    "BranchTable",
    "CommitTable",
)


#
# Branches
#


class BranchTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    hash = tables.LinkColumn("nautobot_dolt:commit", args=[A("hash")])
    actions = ButtonsColumn(
        Branch,
        pk_field="name",
        buttons=("checkout",),
        prepend_template="""
        <a href="/?branch={{ record.name }}" class="btn btn-primary btn-xs" title="Checkout Branch">
            checkout
        </a>
        """,
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
        default_columns = fields


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
