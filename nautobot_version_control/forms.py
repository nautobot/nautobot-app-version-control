"""Forms.py defines the set of forms used for creating, deleting, editing, and searching different models."""

from django import forms

from nautobot.users.models import User
from nautobot.utilities.forms import BootstrapMixin, ConfirmationForm, add_blank_choice

from nautobot_version_control.models import Branch, Commit, PullRequest, PullRequestReview
from nautobot_version_control.utils import active_branch, DoltError
from nautobot_version_control.constants import DOLT_DEFAULT_BRANCH


#
# Branches
#


class BranchForm(forms.ModelForm, BootstrapMixin):
    """BranchForm returns a form for the BranchCheckout and BranchEdit views."""

    name = forms.SlugField()
    starting_branch = forms.ModelChoiceField(queryset=Branch.objects.all(), to_field_name="name", required=True)
    creator = forms.ModelChoiceField(
        queryset=User.objects.all(),
        to_field_name="username",
        required=True,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Branch
        fields = [
            "name",
            "starting_branch",
        ]

    def __init__(self, *args, **kwargs):
        # self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        """save overrides an superclass method."""
        self.instance.starting_branch = self.cleaned_data["starting_branch"]
        self.instance.creator = self.cleaned_data["creator"]
        return super().save(*args, **kwargs)


class MergeForm(forms.Form, BootstrapMixin):
    """MergeForm returns a form the merge button on the branch_merge page."""

    source_branch = forms.ModelChoiceField(queryset=Branch.objects.all(), to_field_name="name", required=True)
    destination_branch = forms.ModelChoiceField(queryset=Branch.objects.all(), to_field_name="name", required=True)

    class Meta:
        fields = [
            "source_branch",
            "destination_branch",
        ]


class MergePreviewForm(forms.Form, BootstrapMixin):
    """MergePreviewForm returns a form for previewing branch merges."""

    source_branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        to_field_name="name",
        disabled=True,
    )
    destination_branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        to_field_name="name",
        disabled=True,
    )

    class Meta:
        fields = [
            "source_branch",
            "destination_branch",
        ]


class BranchBulkEditForm(forms.Form, BootstrapMixin):
    """BranchBulkEditForm is a small form for the branch bulk edit view."""

    class Meta:
        model = Branch
        fields = [
            "name",
        ]


class BranchBulkDeleteForm(ConfirmationForm):
    """
    BranchBulkDeleteForm is used for validating the deletion of branches. It has additional checks for preventing
    deletes of the active branch and the DOLT_DEFAULT_BRANCH.
    """

    pk = forms.ModelMultipleChoiceField(queryset=Branch.objects.all(), widget=forms.MultipleHiddenInput)

    def clean_pk(self):
        """clean_pk gets the primary key of the cleaned data and protects against active_branch and default_branch deletions."""
        # TODO: log error messages
        deletes = [str(b) for b in self.cleaned_data["pk"]]
        if active_branch() in deletes:
            raise DoltError(f"Cannot delete active branch: {active_branch()}")
        if DOLT_DEFAULT_BRANCH in deletes:
            raise DoltError(f"Cannot delete primary branch: {DOLT_DEFAULT_BRANCH}")
        return self.cleaned_data["pk"]

    class Meta:
        model = Branch
        fields = [
            "name",
        ]


class BranchFilterForm(forms.Form, BootstrapMixin):
    """BranchFilterForm is used for filtering the branches list page."""

    model = Branch
    field_order = ["q"]
    q = forms.CharField(required=False, label="Search")

    latest_committer = forms.ChoiceField(choices=[], required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["latest_committer"].choices = add_blank_choice(
            Branch.objects.all().values_list("latest_committer", "latest_committer").distinct()
        )


#
# Commits
#


class CommitForm(forms.ModelForm, BootstrapMixin):
    """CommitForm is a form used for the CommitEdit view."""

    class Meta:
        model = Commit
        fields = ["message"]


class CommitFilterForm(forms.Form, BootstrapMixin):
    """CommitFilterForm is used to filter the commit set."""

    model = Commit
    field_order = ["q"]
    q = forms.CharField(required=False, label="Search")
    committer = forms.ChoiceField(choices=[], required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["committer"].choices = Commit.objects.all().values_list("committer", "committer").distinct()


class CommitBulkRevertForm(forms.Form, BootstrapMixin):
    """CommitBulkRevertForm is used to confirm the deletion of a certain amount of Commits."""

    pk = forms.ModelMultipleChoiceField(queryset=Commit.objects.all(), widget=forms.MultipleHiddenInput())

    class Meta:
        fields = ["branch"]


#
# PullRequests
#


class PullRequestForm(forms.ModelForm, BootstrapMixin):
    """PullRequestForms is used to confirm the creation or addition of pull requests."""

    qs = Branch.objects.exclude(name__startswith="xxx")
    source_branch = forms.ModelChoiceField(queryset=qs, to_field_name="name", required=True)
    destination_branch = forms.ModelChoiceField(queryset=qs, to_field_name="name", required=True)

    class Meta:
        model = PullRequest
        fields = [
            "title",
            "source_branch",
            "destination_branch",
            "description",
        ]


class PullRequestDeleteForm(ConfirmationForm):
    """PullRequestDeleteForm is used to delete selection PRs."""

    pk = forms.ModelMultipleChoiceField(queryset=PullRequest.objects.all(), widget=forms.MultipleHiddenInput)

    def clean_pk(self):
        """clean_pk returns only the pk of the cleaned data"""
        return self.cleaned_data["pk"]

    class Meta:
        model = PullRequest
        fields = [
            "pk",
        ]


class PullRequestFilterForm(forms.Form, BootstrapMixin):
    """PullRequestFilterForm is used to filter the complete PullRequest filter list."""

    model = PullRequest
    q = forms.CharField(required=False, label="Search")
    state = forms.MultipleChoiceField(required=False, choices=PullRequest.PR_STATE_CHOICES)
    creator = forms.ModelChoiceField(required=False, queryset=User.objects.all())
    reviewer = forms.ModelChoiceField(required=False, queryset=User.objects.all())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if args is not None:
            if not args[0].get("state", None):
                new_args = args[0].copy()
                new_args.update({"state": PullRequest.OPEN})
                super().__init__(new_args, **kwargs)

    class Meta:
        fields = [
            "state",
            "title",
            "source_branch",
            "destination_branch",
            "description",
        ]


class PullRequestReviewForm(forms.ModelForm, BootstrapMixin):
    """PullRequestReviewForm is used to review a pull request."""

    class Meta:
        model = PullRequestReview
        fields = [
            "pull_request",
            "summary",
            "state",
        ]
