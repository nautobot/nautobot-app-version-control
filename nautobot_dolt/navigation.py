# navigation.py
from nautobot.extras.plugins import PluginMenuButton, PluginMenuItem
from nautobot.utilities.choices import ButtonColorChoices


menu_items = (
    PluginMenuItem(
        link="plugins:nautobot_dolt:branch_list",
        link_text="Branches",
        buttons=(
            PluginMenuButton(
                "plugins:nautobot_dolt:branch_add",
                "Create Branch",
                "mdi mdi-plus-thick",
                ButtonColorChoices.GREEN,
            ),
        ),
    ),
    PluginMenuItem(
        link="plugins:nautobot_dolt:commit_list",
        link_text="Commits",
        buttons=(
            PluginMenuButton(
                "plugins:nautobot_dolt:commit_add",
                "Create Commit",
                "mdi mdi-plus-thick",
                ButtonColorChoices.GREEN,
            ),
        ),
    ),
)
