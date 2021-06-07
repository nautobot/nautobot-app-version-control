from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views import View

from nautobot.core.views import generic
from nautobot.utilities.utils import normalize_querydict
from nautobot.utilities.views import GetReturnURLMixin

from dolt import filters, forms, tables
from dolt.constants import DOLT_DEFAULT_BRANCH, DOLT_BRANCH_KEYWORD
from dolt.diff.factory import DiffModelFactory
from dolt.diff.util import diffable_content_types
from dolt.models import Branch, Commit


#
# Branches
#


class BranchView(generic.ObjectView):
    queryset = Branch.objects.all()

    def get_extra_context(self, request, instance):
        merge_base = Commit.objects.merge_base(DOLT_DEFAULT_BRANCH, instance.name)
        commit_range = list(
            Commit.objects.filter(
                # todo(andy) selecting by date-range may break for non-linear histories
                date__gt=merge_base.date
            ).values_list("commit_hash", flat=True)
        )

        # todo(andy): hack to work around Dolt bug
        commit_range.append(merge_base.commit_hash)

        results = []
        for dt in diffable_content_types():
            diff_factory = DiffModelFactory(dt)
            queryset = diff_factory.get_model().objects.filter(
                Q(dolt_commit="WORKING")
                | Q(
                    change_type__in=("added", "after"),
                    dolt_commit__in=commit_range[:-1],
                )
                | Q(change_type__in=("removed", "before"), dolt_commit__in=commit_range)
            )

            # todo: factor out a common method
            if not queryset.count():
                continue

            table = diff_factory.make_table_model()
            results.append(
                {
                    "name": f"{dt.model_class()._meta.verbose_name.capitalize()} Diffs",
                    "table": table(queryset, orderable=False),
                    "added": queryset.filter(change_type="added").count(),
                    "modified": queryset.filter(change_type="before").count(),
                    "removed": queryset.filter(change_type="removed").count(),
                }
            )

        return {"results": results}


class BranchListView(generic.ObjectListView):
    queryset = Branch.objects.all()
    filterset = filters.BranchFilterSet
    filterset_form = forms.BranchFilterForm
    table = tables.BranchTable
    action_buttons = ("add",)
    template_name = "dolt/branch_list.html"


class BranchEditView(generic.ObjectEditView):
    queryset = Branch.objects.all()
    model_form = forms.BranchForm
    template_name = "dolt/branch_edit.html"

    def get(self, request, *args, **kwargs):
        initial = {
            "starting_branch": Branch.objects.get(name=DOLT_DEFAULT_BRANCH),
        }
        return render(
            request,
            self.template_name,
            {
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": self.model_form(initial=initial),
            },
        )

    def post(self, request, *args, **kwargs):
        form = self.model_form(data=request.POST, files=request.FILES)
        if form.is_valid():
            # todo: validate db success before updating session
            request.session[DOLT_BRANCH_KEYWORD] = form.cleaned_data.get("name")
        return super().post(request, *args, **kwargs)


class BranchDeleteView(generic.ObjectDeleteView):
    queryset = Branch.objects.all()


class BranchBulkEditView(generic.BulkEditView):
    queryset = Branch.objects.all()
    filterset = filters.BranchFilterSet
    table = tables.BranchTable
    form = forms.BranchBulkEditForm


class BranchBulkDeleteView(generic.BulkDeleteView):
    queryset = Branch.objects.all()
    filterset = filters.BranchFilterSet
    table = tables.BranchTable


#
#   Merge
#


class BranchMergeFormView(GetReturnURLMixin, View):
    queryset = Branch.objects.all()
    form = forms.MergeForm
    template_name = "dolt/branch_merge.html"

    def get(self, request, *args, **kwargs):
        initial = {
            "destination_branch": Branch.objects.get(name=DOLT_DEFAULT_BRANCH),
            "source_branch": Branch.objects.get(name=kwargs["src"]),
        }
        return render(
            request,
            self.template_name,
            {
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": self.form(initial=initial),
            },
        )

    def post(self, request, *args, **kwargs):
        form = self.form(data=request.POST, files=request.FILES)
        if not form.is_valid():
            raise ValueError(form.errors)
        src = form.cleaned_data.get("source_branch")
        dest = form.cleaned_data.get("destination_branch")
        # todo: don't use redirect
        return redirect(
            reverse(
                "plugins:dolt:branch_merge_preview",
                kwargs={"src": src, "dest": dest},
            )
        )


class BranchMergePreView(GetReturnURLMixin, View):
    queryset = Branch.objects.all()
    form = forms.MergePreviewForm
    template_name = "dolt/branch_merge_preview.html"

    def get(self, request, *args, **kwargs):
        src = Branch.objects.get(name=kwargs["src"])
        # render a disabled form with previously submitted data
        initial = {
            "source_branch": src,
            "destination_branch": Branch.objects.get(name=kwargs["dest"]),
        }
        return render(
            request,
            self.template_name,
            {
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": self.form(initial=initial),
                **self.get_extra_context(request, src),
            },
        )

    def post(self, request, *args, **kwargs):
        src = kwargs["src"]
        dest = kwargs["dest"]
        try:
            Branch.objects.get(name=dest).merge(src)
        except Exception as e:
            raise e

        msg = f"<h4>merged branch <b>{src}</b> into <b>{dest}</b></h4>"
        messages.info(request, mark_safe(msg))
        return redirect(f"/?{DOLT_BRANCH_KEYWORD}={dest}")

    def get_extra_context(self, request, instance):
        # todo: need two-dot diff, not three-dot
        merge_base = Commit.objects.merge_base(DOLT_DEFAULT_BRANCH, instance.name)
        commit_range = list(
            Commit.objects.filter(
                # todo(andy) selecting by date-range may break for non-linear histories
                date__gt=merge_base.date
            ).values_list("commit_hash", flat=True)
        )

        # todo(andy): hack to work around Dolt bug
        commit_range.append(merge_base.commit_hash)

        results = []
        for dt in diffable_content_types():
            diff_factory = DiffModelFactory(dt)
            queryset = diff_factory.get_model().objects.filter(
                Q(dolt_commit="WORKING")
                | Q(
                    change_type__in=("added", "after"),
                    dolt_commit__in=commit_range[:-1],
                )
                | Q(change_type__in=("removed", "before"), dolt_commit__in=commit_range)
            )

            # todo: factor out a common method
            if not queryset.count():
                continue

            table = diff_factory.make_table_model()
            results.append(
                {
                    "name": f"{dt.model_class()._meta.verbose_name.capitalize()} Diffs",
                    "table": table(queryset, orderable=False),
                    "added": queryset.filter(change_type="added").count(),
                    "modified": queryset.filter(change_type="before").count(),
                    "removed": queryset.filter(change_type="removed").count(),
                }
            )
        return {"results": results}


#
# Commits
#


class CommitView(generic.ObjectView):
    queryset = Commit.objects.all()

    def get_extra_context(self, request, instance):
        results = []
        for dt in diffable_content_types():
            diff_factory = DiffModelFactory(dt)
            queryset = diff_factory.get_model().objects.filter(
                Q(change_type="added", dolt_commit=instance.commit_hash)
                | Q(change_type="removed", dolt_commit__in=instance.parent_commits)
                | Q(change_type="before", dolt_commit__in=instance.parent_commits)
                | Q(change_type="after", dolt_commit=instance.commit_hash)
            )
            if not queryset.count():
                continue

            table = diff_factory.make_table_model()
            results.append(
                {
                    "name": f"{dt.model_class()._meta.verbose_name.capitalize()} Diffs",
                    "table": table(queryset, orderable=False),
                    "added": queryset.filter(change_type="added").count(),
                    "modified": queryset.filter(change_type="before").count(),
                    "removed": queryset.filter(change_type="removed").count(),
                }
            )

        return {"results": results}


class CommitListView(generic.ObjectListView):
    queryset = Commit.objects.all()
    filterset = filters.CommitFilterSet
    filterset_form = forms.CommitFilterForm
    table = tables.CommitTable
    action_buttons = ("add",)


class CommitEditView(generic.ObjectEditView):
    queryset = Commit.objects.all()
    model_form = forms.CommitForm
    template_name = "dolt/commit_edit.html"


class CommitDeleteView(generic.ObjectDeleteView):
    queryset = Commit.objects.all()
