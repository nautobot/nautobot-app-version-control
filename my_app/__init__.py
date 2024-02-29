"""App declaration for my_app."""
# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

from nautobot.apps import NautobotAppConfig

__version__ = metadata.version(__name__)


class NautobotVersionControlConfig(NautobotAppConfig):
    """App configuration for the my_app app."""

    name = "my_app"
    verbose_name = "Nautobot Version Control"
    version = __version__
    author = "Network to Code, LLC"
    description = "Nautobot Version Control with Dolt."
    base_url = "version-control"
    required_settings = []
    min_version = "2.0.3"
    max_version = "2.9999"
    default_settings = {}
    caching_config = {}


config = NautobotVersionControlConfig  # pylint:disable=invalid-name
