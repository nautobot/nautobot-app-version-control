# navigation.py
from nautobot.extras.plugins import PluginMenuButton, PluginMenuItem
from nautobot.utilities.choices import ButtonColorChoices


menu_items = (
    PluginMenuItem(
        link="plugins:dolt:branch_list",
        link_text="Branches",
        buttons=(
            PluginMenuButton(
                "plugins:dolt:branch_add",
                "Create Branch",
                "mdi mdi-plus-thick",
                ButtonColorChoices.GREEN,
            ),
        ),
    ),
    PluginMenuItem(
        link="plugins:dolt:commit_list",
        link_text="Commits",
    ),
)
