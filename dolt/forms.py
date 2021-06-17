from django import forms

from nautobot.utilities.forms import BootstrapMixin, ConfirmationForm

from dolt.models import Branch, Commit


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
        data = self.cleaned_data["pk"]
        if Branch.active_branch() in [str(b) for b in data]:
            raise forms.ValidationError("The Active Branch can't be deleted")
        return data

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
