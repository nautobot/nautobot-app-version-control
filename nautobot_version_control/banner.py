"""Injection of branch information banner via the Plugins API."""

from django.utils.html import format_html

from nautobot.extras.choices import BannerClassChoices
from nautobot.extras.plugins import PluginBanner

from nautobot_version_control.constants import DOLT_BRANCH_KEYWORD
from nautobot_version_control.utils import active_branch


def banner(context, *args, **kwargs):
    """Show a banner indicating the current active branch, if the user is logged in."""
    if not context.request.user.is_authenticated:
        return None
    branch_name = active_branch()
    return PluginBanner(
        content=format_html(
            """
<div class="text-center">
    Active Branch: <strong>{}</strong>
    <div class = "pull-right">
        <div class="btn btn-xs btn-primary" id="branch-share-button">
            Share
        </div>
    </div>
</div>
<script>
    const btn = document.getElementById("branch-share-button");
    btn.addEventListener('click', ()=>{{
        const currLink = window.location.href;
        const copiedLink = currLink + "?{}={}";
        navigator.clipboard.writeText(copiedLink);
        btn.textContent = "Copied!"
    }});
</script>""",
            branch_name,
            DOLT_BRANCH_KEYWORD,
            branch_name,
        ),
        banner_class=BannerClassChoices.CLASS_INFO,
    )
