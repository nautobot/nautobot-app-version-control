"""Plugin declaration for nautobot_version_control."""
# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

__version__ = metadata.version(__name__)

from nautobot.extras.plugins import NautobotAppConfig


class NautobotVersionControlConfig(NautobotAppConfig):
    """Plugin configuration for the nautobot_version_control plugin."""

    name = "nautobot_version_control"
    verbose_name = "Nautobot Version Control"
    version = __version__
    author = "Network to Code, LLC"
    description = "Nautobot Version Control with Dolt."
    base_url = "version-control"
    required_settings = []
    min_version = "1.2.4"
    max_version = "1.9999"
    default_settings = {}
    caching_config = {}


config = NautobotVersionControlConfig  # pylint:disable=invalid-name
