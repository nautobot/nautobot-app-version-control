from nautobot.core.api import OrderedDefaultRouter
from . import views


router = OrderedDefaultRouter()
router.APIRootView = views.VCSRootView

# Sites
router.register("branches", views.BranchViewSet)
router.register("commits", views.CommitViewSet)
router.register("pull_requests", views.PullRequestViewSet)
router.register("pull_requests_comments", views.PullRequestCommentsViewSet)

app_name = "dolt-api"
urlpatterns = router.urls
