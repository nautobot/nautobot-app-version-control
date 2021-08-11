from django import forms
from django.db.models import ProtectedError

from nautobot.utilities.forms import BootstrapMixin, ConfirmationForm

from dolt.models import Branch, Commit, PullRequest, PullRequestReview
from dolt.constants import DOLT_DEFAULT_BRANCH


#
# Branches
#


class BranchForm(forms.ModelForm, BootstrapMixin):
    name = forms.SlugField()
    starting_branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(), to_field_name="name", required=True
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
        # self.instance.user = self.user
        self.instance.starting_branch = self.cleaned_data["starting_branch"]
        return super().save(*args, **kwargs)


class MergeForm(forms.Form, BootstrapMixin):
    source_branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(), to_field_name="name", required=True
    )
    destination_branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(), to_field_name="name", required=True
    )

    class Meta:
        fields = [
            "source_branch",
            "destination_branch",
        ]


class MergePreviewForm(forms.Form, BootstrapMixin):
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
    class Meta:
        model = Branch
        fields = [
            "name",
        ]


class BranchBulkDeleteForm(ConfirmationForm):
    pk = forms.ModelMultipleChoiceField(
        queryset=Branch.objects.all(), widget=forms.MultipleHiddenInput
    )

    def clean_pk(self):
        # TODO: log error messages
        deletes = [str(b) for b in self.cleaned_data["pk"]]
        active = Branch.active_branch()
        if active in deletes:
            raise forms.ValidationError(f"Cannot delete active branch: {active}")
        if DOLT_DEFAULT_BRANCH in deletes:
            raise forms.ValidationError(
                f"Cannot delete primary branch: {DOLT_DEFAULT_BRANCH}"
            )
        return self.cleaned_data["pk"]

    class Meta:
        model = Branch
        fields = [
            "name",
        ]


class BranchFilterForm(forms.Form, BootstrapMixin):
    model = Branch
    field_order = ["q"]
    q = forms.CharField(required=False, label="Search")


#
# Commits
#


class CommitForm(forms.ModelForm, BootstrapMixin):
    class Meta:
        model = Commit
        fields = ["message"]


class CommitFilterForm(forms.Form, BootstrapMixin):
    model = Commit
    field_order = ["q"]
    q = forms.CharField(required=False, label="Search")


#
# PullRequests
#


class PullRequestForm(forms.ModelForm, BootstrapMixin):
    source_branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(), to_field_name="name", required=True
    )
    destination_branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(), to_field_name="name", required=True
    )

    class Meta:
        model = PullRequest
        fields = [
            "title",
            "source_branch",
            "destination_branch",
            "description",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        # todo: not working yet
        self.instance.creator = kwargs.pop("user", None)
        return super().save(*args, **kwargs)


class PullRequestFilterForm(forms.Form, BootstrapMixin):
    model = PullRequest
    field_order = ["q"]
    q = forms.CharField(required=False, label="Search")

    class Meta:
        fields = ["title", "source_branch", "destination_branch", "description"]


class PullRequestReviewForm(forms.ModelForm, BootstrapMixin):

    class Meta:
        model = PullRequestReview
        fields = [
            "pull_request",
            "summary",
            "state",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        # todo: not working yet
        self.instance.reviewer = kwargs.pop("user", None)
        return super().save(*args, **kwargs)
