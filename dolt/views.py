import json

from django.forms import ValidationError
from django.contrib import messages
from django.db import models, connections
from django.db.models import Q, F, Subquery, OuterRef, Value
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.serializers import serialize
from django.shortcuts import get_list_or_404, render, redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views import View

from nautobot.core.views import generic
from nautobot.dcim.models.sites import Site
from nautobot.extras.utils import is_taggable
from nautobot.utilities.permissions import get_permission_for_model
from nautobot.utilities.views import GetReturnURLMixin, ObjectPermissionRequiredMixin

from dolt import diffs, filters, forms, merge, tables
from dolt.constants import DOLT_DEFAULT_BRANCH, DOLT_BRANCH_KEYWORD
from dolt.versioning import db_for_commit, query_on_branch, change_branches
from dolt.diffs import content_type_has_diff_view_table
from dolt.middleware import branch_from_request
from dolt.models import (
    Branch,
    BranchMeta,
    Commit,
    CommitAncestor,
    PullRequest,
    PullRequestReview,
)


#
# Branches
#


class BranchView(generic.ObjectView):
    queryset = Branch.objects.all()

    def get_extra_context(self, req, instance):
        merge_base = Commit.merge_base(DOLT_DEFAULT_BRANCH, instance.name)
        head = instance.hash
        return {"results": diffs.two_dot_diffs(from_commit=merge_base, to_commit=head)}


class BranchListView(generic.ObjectListView):
    queryset = Branch.objects.exclude(name__startswith="xxx")
    filterset = filters.BranchFilterSet
    filterset_form = forms.BranchFilterForm
    table = tables.BranchTable
    action_buttons = ("add",)
    template_name = "dolt/branch_list.html"


class BranchCheckoutView(View):
    queryset = Branch.objects.all()
    model_form = forms.BranchForm
    template_name = "dolt/branch_edit.html"

    def get(self, req, *args, **kwargs):
        # new branch will be checked out on redirect
        change_branches(sess=req.session, branch=kwargs["pk"])
        return redirect("/")


class BranchEditView(generic.ObjectEditView):
    queryset = Branch.objects.all()
    model_form = forms.BranchForm
    template_name = "dolt/branch_edit.html"

    def get(self, req, *args, **kwargs):
        initial = {
            "starting_branch": Branch.objects.get(name=DOLT_DEFAULT_BRANCH),
        }
        return render(
            req,
            self.template_name,
            {
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": self.model_form(initial=initial),
            },
        )

    def post(self, req, *args, **kwargs):
        form = self.model_form(data=req.POST, files=req.FILES)
        response = super().post(req, *args, **kwargs)
        if self._is_success_response(response):
            change_branches(sess=req.session, branch=form.data.get("name"))
        return response

    def _is_success_response(self, response):
        return (response.status_code // 100) in (2, 3)

    # TODO: create branch meta on branch creation
    # def _create_branch_meta(self, form, user):
    #     branch = Branch.objects.get(name=form.data.get("name"))
    #     with query_on_branch(branch):
    #         # branch meta needs to live on the branch it describes
    #         BranchMeta(
    #             branch=branch.name,
    #             source_branch=form.data.get("starting_branch"),
    #             author=user,
    #         ).save()


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

    def get(self, req, *args, **kwargs):
        initial = {
            # TODO: use branch meta source branch
            "destination_branch": Branch.objects.get(name=DOLT_DEFAULT_BRANCH),
            "source_branch": Branch.objects.get(name=kwargs["src"]),
        }
        return render(
            req,
            self.template_name,
            {
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": self.form(initial=initial),
            },
        )

    def post(self, req, *args, **kwargs):
        form = self.form(data=req.POST, files=req.FILES)
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

    def get(self, req, *args, **kwargs):
        src = Branch.objects.get(name=kwargs["src"])
        dest = Branch.objects.get(name=kwargs["dest"])
        # render a disabled form with previously submitted data
        initial = {
            "source_branch": src,
            "destination_branch": Branch.objects.get(name=kwargs["dest"]),
        }
        return render(
            req,
            self.template_name,
            {
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": self.form(initial=initial),
                **self.get_extra_context(req, src, dest),
            },
        )

    def post(self, req, *args, **kwargs):
        src = kwargs["src"]
        dest = kwargs["dest"]
        try:
            Branch.objects.get(name=dest).merge(src, user=req.user)
        except Exception as e:
            messages.error(req, mark_safe(f"error during merge: {str(e)}"))
            return redirect(req.path)
        else:
            msg = f"<h4>merged branch <b>{src}</b> into <b>{dest}</b></h4>"
            messages.info(req, mark_safe(msg))
            change_branches(sess=req.session, branch=dest)
            return redirect(f"/")

    def get_extra_context(self, req, src, dest):
        merge_base = Commit.merge_base(src, dest)
        source_head = src.hash
        return {
            "results": diffs.two_dot_diffs(
                from_commit=merge_base, to_commit=source_head
            ),
            "conflicts": merge.get_conflicts_for_merge(src, dest),
            "back_btn_url": reverse("plugins:dolt:branch_merge", args=[src.name]),
        }


#
# Commits
#


class CommitView(generic.ObjectView):
    queryset = Commit.objects.all()

    def get(self, request, *args, **kwargs):
        """
        Looks up the requested commit using a database revision
        to ensure the commit is accessible.
        todo: explain ancestor
        """
        anc = get_list_or_404(CommitAncestor.objects.all(), **kwargs)[0]
        db = db_for_commit(anc.commit_hash)
        instance = self.queryset.using(db).get(commit_hash=anc.commit_hash)

        if anc.parent_hash:
            diff = diffs.two_dot_diffs(from_commit=anc.parent_hash, to_commit=instance)
        else:
            # init commit has no parents
            diff = {}

        return render(
            request,
            self.get_template_name(),
            {
                "object": instance,
                "results": diff,
            },
        )


class CommitListView(generic.ObjectListView):
    queryset = Commit.objects.all()
    filterset = filters.CommitFilterSet
    filterset_form = forms.CommitFilterForm
    table = tables.CommitTable
    template_name = "dolt/commits.html"
    action_buttons = None

    def alter_queryset(self, req):
        if Branch.active_branch() != DOLT_DEFAULT_BRANCH:
            # only list commits on the current branch since the merge-base
            merge_base_hash = Commit.merge_base(
                DOLT_DEFAULT_BRANCH, Branch.active_branch()
            )
            merge_base = Commit.objects.get(commit_hash=merge_base_hash)
            self.queryset = self.queryset.filter(date__gt=merge_base.date)
        return self.queryset

    def extra_context(self):
        return {"active_branch": Branch.active_branch()}


class CommitEditView(generic.ObjectEditView):
    queryset = Commit.objects.all()
    model_form = forms.CommitForm
    template_name = "dolt/commit_edit.html"


class CommitDeleteView(generic.ObjectDeleteView):
    queryset = Commit.objects.all()


#
# Diffs
#


class ActiveBranchDiffs(View):
    def get(self, *args, **kwargs):
        return redirect(
            reverse(
                "plugins:dolt:branch",
                kwargs={
                    "pk": Branch.active_branch(),
                },
            )
        )


class DiffDetailView(View):
    template_name = "dolt/diff_detail.html"

    def get_required_permission(self):
        return get_permission_for_model(Site, "view")

    def get(self, req, *args, **kwargs):
        self.model = self.get_model(kwargs)
        return render(
            req,
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

        from_qs = qs.using(db_for_commit(from_commit))
        if from_qs.filter(pk=pk).exists():
            before_obj = serialize_object(from_qs.get(pk=pk))
        else:
            before_obj, added = {}, True

        to_qs = qs.using(db_for_commit(to_commit))
        if to_qs.filter(pk=pk).exists():
            after_obj = serialize_object(to_qs.get(pk=pk))
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

                diff_obj.append(
                    {
                        "name": field,
                        "before_val": before_val,
                        "before_style": before_style,
                        "after_val": after_val,
                        "after_style": after_style,
                    }
                )

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


#
# Pull Requests
#


class PullRequestListView(generic.ObjectListView):
    queryset = PullRequest.objects.all()
    filterset = filters.PullRequestFilterSet
    filterset_form = forms.PullRequestFilterForm
    table = tables.PullRequestTable
    # action_buttons = ("add",)  # todo: add button
    action_buttons = ()
    template_name = "dolt/pull_request/pull_request_list.html"


class PullRequestDiffView(generic.ObjectView):
    queryset = PullRequest.objects.all()
    template_name = "dolt/pull_request/diffs.html"

    def get_extra_context(self, req, obj, **kwargs):
        head = Branch.objects.get(name=obj.source_branch).hash
        merge_base = Commit.merge_base(obj.source_branch, obj.destination_branch)
        return {
            "active_tab": "diffs",
            "results": diffs.two_dot_diffs(from_commit=merge_base, to_commit=head),
        }


class PullRequestConflictView(generic.ObjectView):
    queryset = PullRequest.objects.all()
    template_name = "dolt/pull_request/conflicts.html"

    def get_extra_context(self, req, obj, **kwargs):
        return {"active_tab": "conflicts", "results": {}}


class PullRequestEditView(generic.ObjectEditView):
    queryset = PullRequest.objects.all()
    model_form = forms.PullRequestForm
    template_name = "dolt/pull_request/edit.html"

    def get(self, req, *args, **kwargs):
        initial = {
            "destination_branch": Branch.objects.get(name=DOLT_DEFAULT_BRANCH),
        }
        return render(
            req,
            self.template_name,
            {
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": self.model_form(initial=initial),
            },
        )

    def post(self, req, *args, **kwargs):
        # todo: user not displaying
        kwargs["user"] = req.user
        return super().post(req, *args, **kwargs)


class PullRequestMergeView(generic.ObjectView):
    queryset = PullRequest.objects.all()
    template_name = ""


class PullRequestCloseView(generic.ObjectView):
    queryset = PullRequest.objects.all()
    template_name = ""


class PullRequestReviewListView(generic.ObjectView):
    queryset = PullRequest.objects.all()
    table = tables.PullRequestReviewTable
    template_name = "dolt/pull_request/review_list.html"

    def get_extra_context(self, req, obj):
        reviews = PullRequestReview.objects.filter(pull_request=obj.pk).order_by("reviewed_at")
        return {
            "active_tab": "reviews",
            "review_list": reviews,
        }


class PullRequestReviewEditView(generic.ObjectEditView):
    queryset = PullRequestReview.objects.all()
    model_form = forms.PullRequestReviewForm
    template_name = "dolt/pull_request/review_edit.html"

    def get(self, req, *args, **kwargs):
        initial = {
            "pull_request": PullRequest.objects.get(pk=kwargs["pull_request"]),
        }
        return render(
            req,
            self.template_name,
            {
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": self.model_form(initial=initial),
            },
        )

    def post(self, req, *args, **kwargs):
        kwargs["user"] = req.user
        return super().post(req, *args, **kwargs)


class PullRequestCommitListView(generic.ObjectView):
    queryset = PullRequest.objects.all()
    table = tables.CommitTable
    template_name = "dolt/pull_request/commits.html"
    action_buttons = ()

    def get_extra_context(self, req, obj, **kwargs):
        return {
            "active_tab": "commits",
            "commit_list": self.table(obj.commits),
        }
