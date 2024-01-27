"""Navigation items for the top level nav bar."""


from nautobot.core.apps import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab

menu_items = (
    NavMenuTab(
        name="Version Control",
        weight=1000,
        groups=(
            NavMenuGroup(
                name="Version Control",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_version_control:branch_list",
                        name="Branches",
                        permissions=["nautobot_version_control.view_branch"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_version_control:branch_add",
                                permissions=["nautobot_version_control.add_branch"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_version_control:pull_request_list",
                        name="Pull Requests",
                        permissions=["nautobot_version_control.view_pullrequest"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_version_control:pull_request_add",
                                permissions=["nautobot_version_control.add_pullrequest"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_version_control:commit_list",
                        name="Commits (Active Branch)",
                        permissions=["nautobot_version_control.view_commit"],
                        buttons=(),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_version_control:active_branch_diffs",
                        name="Diffs (Active Branch)",
                        permissions=["nautobot_version_control.view_diff"],
                        buttons=(),
                    ),
                ),
            ),
        ),
    ),
)
