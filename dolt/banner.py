from django.utils.html import format_html

from nautobot.extras.choices import BannerClassChoices
from nautobot.extras.plugins import PluginBanner

from dolt.models import Branch


def dolt_banner(context, *args, **kwargs):
    """Display the Active Branch, if logged in."""
    # Request parameters can be accessed via context.request

    if not context.request.user.is_authenticated:
        # No banner if the user isn't logged in
        return None
    else:
        return PluginBanner(
            content=format_html(
                """
                <div class="text-center">
                    Active Branch: <strong>{}</strong>
                </div>
                """,
                Branch.active_branch(),
            ),
            banner_class=BannerClassChoices.CLASS_INFO,
        )
