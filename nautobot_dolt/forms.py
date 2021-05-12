from django import forms

from nautobot.utilities.forms import BootstrapMixin
from nautobot.vcs.models import Branch, Commit


#
# Branches
#


class BranchForm(forms.ModelForm, BootstrapMixin):
    starting_branch = forms.ModelChoiceField(queryset=Branch.objects.all(), to_field_name="name", required=True)

    class Meta:
        model = Branch
        fields = [
            "name",
            "starting_branch",
        ]

    def save(self, *args, **kwargs):
        self.instance.starting_branch = self.cleaned_data["starting_branch"]
        return super().save(*args, **kwargs)


class MergeForm(forms.Form, BootstrapMixin):
    dest_branch = forms.ModelChoiceField(queryset=Branch.objects.all(), to_field_name="name", required=True)
    src_branch = forms.ModelChoiceField(queryset=Branch.objects.all(), to_field_name="name", required=True)

    class Meta:
        fields = [
            "dest_branch",
            "src_branch",
        ]


class BranchBulkEditForm(forms.Form, BootstrapMixin):
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
