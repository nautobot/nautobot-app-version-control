from nautobot.core.api import OrderedDefaultRouter
from . import views


router = OrderedDefaultRouter()
router.APIRootView = views.VCSRootView

# Sites
router.register("branches", views.BranchViewSet)
router.register("commits", views.CommitViewSet)

app_name = "nautobot_dolt-api"
urlpatterns = router.urls
