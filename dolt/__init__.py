from nautobot.extras.plugins import PluginConfig


class NautobotDolt(PluginConfig):
    name = "dolt"
    verbose_name = "Nautobot Dolt"
    description = "Nautobot + Dolt"
    version = "0.1"
    author = "Andy Arthur"
    author_email = "andy@dolthub.com"
    required_settings = []
    default_settings = {}
    middleware = [
        "dolt.middleware.DoltBranchMiddleware",
        "dolt.middleware.DoltAutoCommitMiddleware",
    ]


config = NautobotDolt
