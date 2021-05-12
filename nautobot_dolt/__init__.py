from nautobot.extras.plugins import PluginConfig


class NautobotDolt(PluginConfig):
    name = "nautobot_dolt"
    verbose_name = "Nautobot Plugin Workflow Dolt"
    description = "Nautobot + Dolt"
    version = "0.1"
    author = "Andy Arthur"
    author_email = "andy@dolthub.com"
    base_url = "workflow-dolt"
    required_settings = []
    default_settings = {}


config = NautobotDolt
