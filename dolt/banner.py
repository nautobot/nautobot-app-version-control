from django.utils.html import format_html

from nautobot.extras.choices import BannerClassChoices
from nautobot.extras.plugins import PluginBanner

from dolt.constants import DOLT_BRANCH_KEYWORD
from dolt.models import Branch
from dolt.utils import active_branch


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
                        Active Branch: <strong> {} </strong>
                        <div class = "pull-right">
                            <div class="btn btn-xs btn-primary" id="share-button">
                                Share
                            </div>
                        </div>
                    </div>
                    <script>
                        const b = document.getElementById("share-button");
                        b.addEventListener('click', ()=>{{
                            const currLink = window.location.href;
                            const copiedLink = currLink + "? {} = {} ";
                            navigator.clipboard.writeText(copiedLink);
                            b.textContent = "Copied!"
                        }});
                    </script>
                """,
                active_branch(),
                DOLT_BRANCH_KEYWORD,
                active_branch()
            ),
            banner_class=BannerClassChoices.CLASS_INFO,
        )
