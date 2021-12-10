"""navigation.py contains the navigation items for the top level nav bar."""


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
                        permissions=[],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_version_control:branch_add",
                                permissions=[],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_version_control:pull_request_list",
                        name="Pull Requests",
                        permissions=[],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_version_control:pull_request_add",
                                permissions=[],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_version_control:commit_list",
                        name="Commits (Active Branch)",
                        permissions=[],
                        buttons=(),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_version_control:active_branch_diffs",
                        name="Diffs (Active Branch)",
                        permissions=[],
                        buttons=(),
                    ),
                ),
            ),
        ),
    ),
)
