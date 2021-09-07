import django_filters
from django.db.models import Q

from nautobot.utilities.filters import BaseFilterSet
from dolt.models import Branch, Commit, PullRequest, PullRequestReview


class BranchFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )

    class Meta:
        model = Branch
        fields = (
            "name",
            "hash",
            "latest_committer",
            "latest_committer_email",
            "latest_commit_date",
            "latest_commit_message",
        )

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(hash__icontains=value)
            | Q(latest_committer__icontains=value)
            | Q(latest_committer_email__icontains=value)
            | Q(latest_commit_date__icontains=value)
            | Q(latest_commit_message__icontains=value)
        )


class CommitFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )

    class Meta:
        model = Commit
        fields = (
            "commit_hash",
            "committer",
            "email",
            "date",
            "message",
        )

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(commit_hash__icontains=value)
            | Q(committer__icontains=value)
            | Q(email__icontains=value)
            | Q(date__icontains=value)
            | Q(message__icontains=value)
        )


class PullRequestFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )

    class Meta:
        model = PullRequest
        fields = (
            "title",
            "state",
            "source_branch",
            "destination_branch",
            "description",
            "creator",
        )

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value)
            | Q(source_branch__icontains=value)
            | Q(destination_branch__icontains=value)
            | Q(description__icontains=value)
            | Q(creator__icontains=value)
        )


class PullRequestCommentFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )

    class Meta:
        model = PullRequestReview
        # todo: pull request id
        fields = (
            "pull_request",
            "reviewer",
            "state",
            "reviewed_at",
            "summary",
        )

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(reviewer__icontains=value)
            | Q(reviewed_at__icontains=value)
            | Q(state__icontains=PullRequestReview.COMMENTED)
            | Q(summary__icontains=value)
        )
