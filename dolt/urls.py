from django.urls import path

from dolt import views

urlpatterns = [
    # Branches
    path("branches/", views.BranchListView.as_view(), name="branch_list"),
    path("branches/add/", views.BranchEditView.as_view(), name="branch_add"),
    path("branches/edit/", views.BranchBulkEditView.as_view(), name="branch_bulk_edit"),
    path(
        "branches/delete/",
        views.BranchBulkDeleteView.as_view(),
        name="branch_bulk_delete",
    ),
    path(
        "branches/<str:src>/merge/",
        views.BranchMergeFormView.as_view(),
        name="branch_merge",
    ),
    path(
        "branches/<str:src>/merge/<str:dest>",
        views.BranchMergePreView.as_view(),
        name="branch_merge_preview",
    ),
    path("branches/<str:pk>/", views.BranchView.as_view(), name="branch"),
    path("branches/<str:pk>/edit/", views.BranchEditView.as_view(), name="branch_edit"),
    path(
        "branches/<str:pk>/delete/",
        views.BranchDeleteView.as_view(),
        name="branch_delete",
    ),
    # Commits
    path("commits/", views.CommitListView.as_view(), name="commit_list"),
    path("commits/add/", views.CommitEditView.as_view(), name="commit_add"),
    path("commits/<str:pk>/", views.CommitView.as_view(), name="commit"),
    path("commits/<str:pk>/edit/", views.CommitEditView.as_view(), name="commit_edit"),
    path(
        "commits/<str:pk>/delete/",
        views.CommitDeleteView.as_view(),
        name="commit_delete",
    ),
]
