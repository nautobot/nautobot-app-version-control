# navigation.py
from nautobot.core.apps import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab
from nautobot.utilities.choices import ButtonColorChoices


menu_items = (
    NavMenuTab(
        name="Dolt",
        weight=1000,
        groups=(
            NavMenuGroup(
                name="version control",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:dolt:branch_list",
                        name="Branches",
                        permissions=[],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:dolt:branch_add",
                                permissions=[],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:dolt:pull_request_list",
                        name="Pull Requests",
                        permissions=[],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:dolt:pull_request_add",
                                permissions=[],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:dolt:commit_list",
                        name="Commits (Active Branch)",
                        permissions=[],
                    ),
                    NavMenuItem(
                        link="plugins:dolt:active_branch_diffs",
                        name="Diffs (Active Branch)",
                        permissions=[],
                    ),
                ),
            ),
        ),
    ),
)
