"""Filters.py defines a set of Filters needed for each model defined in models.py."""

import django_filters
from django.db.models import Q

from nautobot.utilities.filters import BaseFilterSet
from nautobot_version_control.models import Branch, Commit, PullRequest, PullRequestReview


class BranchFilterSet(BaseFilterSet):
    """BranchFilterSet returns a filter for the Branch model."""

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

    def search(self, queryset, name, value):  # pylint: disable=unused-argument,no-self-use
        """
        search performs an ORM filter on the Branch model
        :param queryset: The Branch queryset
        :param name: The modelname
        :param value: The value to be searched for
        :return: A filtered queryset
        """
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
    """CommitFilterSet returns a filter for the CommitFilterSet."""

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

    def search(self, queryset, name, value):  # pylint: disable=unused-argument,no-self-use
        """
        search performs an ORM filter on the Commit model
        :param queryset: The Commit queryset
        :param name: The modelname
        :param value: The value to be searched for
        :return: A filtered queryset
        """
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
    """PullRequestFilterSet returns a filter for the PullRequest model."""

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

    def search(self, queryset, name, value):  # pylint: disable=unused-argument,no-self-use
        """
        search performs an ORM filter on the PullRequestFilterSet model
        :param queryset: The PullRequestFilterSet queryset
        :param name: The modelname
        :param value: The value to be searched for
        :return: A filtered queryset
        """
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value)
            | Q(state__icontains=value)
            | Q(source_branch__icontains=value)
            | Q(destination_branch__icontains=value)
            | Q(description__icontains=value)
            | Q(creator__icontains=value)
        )


class PullRequestDefaultOpenFilterSet(PullRequestFilterSet):
    """PullRequestDefaultOpenFilterSet returns a filter for the PullRequest model where the default search is state=OPEN."""

    state = django_filters.MultipleChoiceFilter(choices=PullRequest.PR_STATE_CHOICES)

    def __init__(self, data, *args, **kwargs):
        if not data.get("state"):
            data = data.copy()
            data["state"] = PullRequest.OPEN
        super().__init__(data, *args, **kwargs)


class PullRequestReviewFilterSet(BaseFilterSet):
    """PullRequestReviewFilterSet returns a filter for the PullRequestReview model."""

    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )
    state = django_filters.MultipleChoiceFilter(choices=PullRequest.PR_STATE_CHOICES)

    class Meta:
        model = PullRequestReview
        fields = (
            "pull_request",
            "reviewer",
            "state",
            "reviewed_at",
            "summary",
        )

    def search(self, queryset, name, value):  # pylint: disable=unused-argument,no-self-use
        """
        search performs an ORM filter on the PullRequestReviewFilterSet model
        :param queryset: The PullRequestReviewFilterSet queryset
        :param name: The modelname
        :param value: The value to be searched for
        :return: A filtered queryset
        """
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(reviewer__icontains=value)
            | Q(reviewed_at__icontains=value)
            | Q(state__icontains=value)
            | Q(summary__icontains=value)
        )
