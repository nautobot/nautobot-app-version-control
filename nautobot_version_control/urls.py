"""urls.py contains the main routing for the Nautobot Version Control plugin."""


from django.urls import path

from nautobot_version_control import views

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
    path(
        "branches/<str:pk>/checkout/",
        views.BranchCheckoutView.as_view(),
        name="branch_checkout",
    ),
    path("branches/<str:pk>/edit/", views.BranchEditView.as_view(), name="branch_edit"),
    # Commits
    path("commits/", views.CommitListView.as_view(), name="commit_list"),
    path("commits/add/", views.CommitEditView.as_view(), name="commit_add"),
    path(
        "commits/revert/",
        views.CommitRevertView.as_view(),
        name="commit_revert",
    ),
    path("commits/<str:pk>/", views.CommitView.as_view(), name="commit"),
    path("commits/<str:pk>/edit/", views.CommitEditView.as_view(), name="commit_edit"),
    path(
        "commits/<str:pk>/delete/",
        views.CommitDeleteView.as_view(),
        name="commit_delete",
    ),
    path(
        "dynamic/<str:from_commit>/<str:to_commit>/<str:app_label>/<str:model>/<str:pk>/",
        views.DiffDetailView.as_view(),
        name="diff_detail",
    ),
    # Diffs
    path("diffs/", views.ActiveBranchDiffs.as_view(), name="active_branch_diffs"),
    # Pull Requests
    path("pull-request/", views.PullRequestListView.as_view(), name="pull_request_list"),
    path(
        "pull-request/add/",
        views.PullRequestEditView.as_view(),
        name="pull_request_add",
    ),
    path(
        "pull-request/delete/",
        views.PullRequestBulkDeleteView.as_view(),
        name="pullrequest_bulk_delete",
    ),
    path(
        "pull-request/<str:pk>/",
        views.PullRequestDiffView.as_view(),
        name="pull_request",
    ),
    path(
        "pull-request/<str:pk>/edit",
        views.PullRequestEditView.as_view(),
        name="pull_request_edit",
    ),
    path(
        "pull-request/<str:pk>/merge",
        views.PullRequestMergeView.as_view(),
        name="pull_request_merge",
    ),
    path(
        "pull-request/<str:pk>/close",
        views.PullRequestCloseView.as_view(),
        name="pull_request_close",
    ),
    path(
        "pull-request/<str:pk>/conflicts",
        views.PullRequestConflictView.as_view(),
        name="pull_request_conflicts",
    ),
    path(
        "pull-request/<str:pk>/reviews",
        views.PullRequestReviewListView.as_view(),
        name="pull_request_reviews",
    ),
    path(
        "pull-request/<str:pull_request>/reviews/add/",
        views.PullRequestReviewEditView.as_view(),
        name="pull_request_add_review",
    ),
    path(
        "pull-request/<str:pk>/commits",
        views.PullRequestCommitListView.as_view(),
        name="pull_request_commits",
    ),
]
