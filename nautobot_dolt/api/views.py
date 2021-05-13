from rest_framework.routers import APIRootView
from nautobot_dolt import filters
from nautobot.extras.api.views import CustomFieldModelViewSet, StatusViewSetMixin
from . import serializers
from nautobot_dolt.models import Branch


class VCSRootView(APIRootView):
    """
    VCS API root view
    """

    def get_view_name(self):
        return "VCS"


#
# Branches
#


class BranchViewSet(CustomFieldModelViewSet):
    queryset = Branch.objects.prefetch_related("tags")
    serializer_class = serializers.BranchSerializer
    filterset_class = filters.BranchFilterSet


#
# Branches
#


class CommitViewSet(CustomFieldModelViewSet):
    queryset = Branch.objects.prefetch_related("tags")
    serializer_class = serializers.CommitSerializer
    filterset_class = filters.CommitFilterSet
