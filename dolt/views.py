import json

from django.contrib import messages
from django.db import models
from django.db.models import Q, F, Subquery, OuterRef, Value
from django.contrib.contenttypes.models import ContentType
from django.core.serializers import serialize
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views import View

from nautobot.core.views import generic
from nautobot.dcim.models.sites import Site
from nautobot.extras.utils import is_taggable
from nautobot.utilities.permissions import get_permission_for_model
from nautobot.utilities.views import GetReturnURLMixin, ObjectPermissionRequiredMixin

from dolt import filters, forms, tables
from dolt.constants import DOLT_DEFAULT_BRANCH, DOLT_BRANCH_KEYWORD
from dolt.context_managers import query_at_commit
from dolt.diff import diffs
from dolt.diff.diffs import content_type_has_diff_view_table
from dolt.models import Branch, Commit


#
# Branches
#


class BranchView(generic.ObjectView):
    queryset = Branch.objects.all()

    def get_extra_context(self, request, instance):
        merge_base = Commit.objects.merge_base(DOLT_DEFAULT_BRANCH, instance.name)
        head = instance.head_commit_hash()
        return {"results": diffs.two_dot_diffs(from_commit=merge_base, to_commit=head)}


class BranchListView(generic.ObjectListView):
    queryset = Branch.objects.all()
    filterset = filters.BranchFilterSet
    filterset_form = forms.BranchFilterForm
    table = tables.BranchTable
    action_buttons = ("add",)
    template_name = "dolt/branch_list.html"


class BranchCheckoutView(View):
    queryset = Branch.objects.all()
    model_form = forms.BranchForm
    template_name = "dolt/branch_edit.html"

    def get(self, request, *args, **kwargs):
        # new branch will be checked out on redirect
        request.session[DOLT_BRANCH_KEYWORD] = kwargs["pk"]
        return redirect("/")


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


class BranchBulkEditView(generic.BulkEditView):
    queryset = Branch.objects.all()
    filterset = filters.BranchFilterSet
    table = tables.BranchTable
    form = forms.BranchBulkEditForm


class BranchBulkDeleteView(generic.BulkDeleteView):
    queryset = Branch.objects.all()
    table = tables.BranchTable
    form = forms.BranchBulkDeleteForm


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
        return redirect(f"/")

    def get_extra_context(self, request, instance):
        # todo: need two-dot diff, not three-dot
        dest_head = Branch.objects.get(name=DOLT_DEFAULT_BRANCH).head_commit_hash()
        source_head = instance.head_commit_hash()
        return {
            "results": diffs.two_dot_diffs(from_commit=dest_head, to_commit=source_head)
        }


#
# Commits
#


class CommitView(generic.ObjectView):
    queryset = Commit.objects.all()

    def get_extra_context(self, request, instance):
        if not len(instance.parent_commits):
            return {}  # init commit has no parents
        parent = Commit.objects.get(commit_hash=instance.parent_commits[0])
        return {"results": diffs.two_dot_diffs(from_commit=parent, to_commit=instance)}


class CommitListView(generic.ObjectListView):
    queryset = Commit.objects.all()
    filterset = filters.CommitFilterSet
    filterset_form = forms.CommitFilterForm
    table = tables.CommitTable
    template_name = "dolt/commit_list.html"
    action_buttons = ("add",)

    def alter_queryset(self, request):
        # only list commits on the current branch since the merge-base
        merge_base = Commit.objects.merge_base(
            DOLT_DEFAULT_BRANCH, Branch.active_branch()
        )
        return self.queryset.filter(date__gt=merge_base.date)

    def get_extra_context(self, request, instance):
        return {"branch": Branch.active_branch()}


class CommitEditView(generic.ObjectEditView):
    queryset = Commit.objects.all()
    model_form = forms.CommitForm
    template_name = "dolt/commit_edit.html"


class CommitDeleteView(generic.ObjectDeleteView):
    queryset = Commit.objects.all()


#
# Diff Detail
#


# todo: re-add permissions
# class DiffDetailView(ObjectPermissionRequiredMixin, View):
class DiffDetailView(View):
    template_name = "dolt/diff_detail.html"

    def get_required_permission(self):
        return get_permission_for_model(Site, "view")

    def get(self, request, *args, **kwargs):
        self.model = self.get_model(kwargs)
        return render(
            request,
            self.template_name,
            {
                "verbose_name": self.display_name(kwargs),
                "diff_obj": self.diff_obj(kwargs),
            },
        )

    def diff_obj(self, kwargs):
        pk = kwargs["pk"]
        from_commit = kwargs["from_commit"]
        to_commit = kwargs["to_commit"]
        qs = self.model.objects.all()

        added, removed = False, False
        with query_at_commit(from_commit):
            if qs.filter(pk=pk).exists():
                before_obj = serialize_object(qs.get(pk=pk))
            else:
                before_obj, added = {}, True
        with query_at_commit(to_commit):
            if qs.filter(pk=pk).exists():
                after_obj = serialize_object(qs.get(pk=pk))
            else:
                after_obj, removed = {}, True

        diff_obj = []
        for field in self.model.csv_headers:
            if field in before_obj or field in after_obj:
                before_val = before_obj.get(field, "")
                after_val = after_obj.get(field, "")

                before_style, after_style = "", ""
                if removed:
                    before_style = "bg-danger"
                elif added:
                    after_style = "bg-success"
                elif before_val != after_val:
                    before_style = "bg-danger"
                    after_style = "bg-success"

                diff_obj.append({
                    "name": field,
                    "before_val": before_val,
                    "before_style": before_style,
                    "after_val": after_val,
                    "after_style": after_style,
                })

        return diff_obj

    def get_model(self, kwargs):
        return ContentType.objects.get(
            app_label=kwargs["app_label"], model=kwargs["model"]
        ).model_class()

    def display_name(self, kwargs):
        return self.get_model(kwargs)._meta.verbose_name.capitalize()

def serialize_object(obj, extra=None, exclude=None):
    """
    Return a generic JSON representation of an object using Django's built-in serializer. (This is used for things like
    change logging, not the REST API.) Optionally include a dictionary to supplement the object data. A list of keys
    can be provided to exclude them from the returned dictionary. Private fields (prefaced with an underscore) are
    implicitly excluded.
    """
    breakpoint()
    json_str = serialize("json", [obj])
    data = json.loads(json_str)[0]["fields"]

    # Include custom_field_data as "custom_fields"
    if hasattr(obj, "_custom_field_data"):
        data["custom_fields"] = data.pop("_custom_field_data")

    # Include any tags. Check for tags cached on the instance; fall back to using the manager.
    if is_taggable(obj):
        tags = getattr(obj, "_tags", []) or obj.tags.all()
        data["tags"] = [tag.name for tag in tags]

    # Append any extra data
    if extra is not None:
        data.update(extra)

    # Copy keys to list to avoid 'dictionary changed size during iteration' exception
    for key in list(data):
        # Private fields shouldn't be logged in the object change
        if isinstance(key, str) and key.startswith("_"):
            data.pop(key)

        # Explicitly excluded keys
        if isinstance(exclude, (list, tuple)) and key in exclude:
            data.pop(key)

    return data