""" navigation.py contains the navigation items for the top level nav bar """


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
                        buttons=(),
                    ),
                    NavMenuItem(
                        link="plugins:dolt:active_branch_diffs",
                        name="Diffs (Active Branch)",
                        permissions=[],
                        buttons=(),
                    ),
                ),
            ),
        ),
    ),
)
