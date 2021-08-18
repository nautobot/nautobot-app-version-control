import json
import logging

from django.forms import ValidationError
from django.contrib import messages
from django.db import models, connections
from django.db.models import Q, F, Subquery, OuterRef, Value
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.serializers import serialize
from django.shortcuts import get_object_or_404, get_list_or_404, render, redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views import View

from nautobot.core.views import generic
from nautobot.dcim.models.sites import Site
from nautobot.extras.utils import is_taggable
from nautobot.utilities.forms import ConfirmationForm
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
    template_name = "dolt/branch_bulk_delete.html"

    def get(self, request):
        return redirect(self.get_return_url(request))

    def post(self, request, **kwargs):
        logger = logging.getLogger("nautobot.views.BulkDeleteView")
        model = self.queryset.model

        # Are we deleting *all* objects in the queryset or just a selected subset?
        if request.POST.get("_all"):
            if self.filterset is not None:
                pk_list = [
                    obj.pk
                    for obj in self.filterset(request.GET, model.objects.only("pk")).qs
                ]
            else:
                pk_list = model.objects.values_list("pk", flat=True)
        else:
            pk_list = request.POST.getlist("pk")

        form_cls = self.get_form()

        if "_confirm" in request.POST:
            form = form_cls(request.POST)
            if form.is_valid():
                logger.debug("Form validation was successful")

                # Delete objects
                queryset = self.queryset.filter(pk__in=pk_list)
                try:
                    deleted_count = queryset.delete()[1][model._meta.label]
                except ProtectedError as e:
                    logger.info(
                        "Caught ProtectedError while attempting to delete objects"
                    )
                    handle_protectederror(queryset, request, e)
                    return redirect(self.get_return_url(request))

                msg = "Deleted {} {}".format(
                    deleted_count, model._meta.verbose_name_plural
                )
                logger.info(msg)
                messages.success(request, msg)
                return redirect(self.get_return_url(request))

            else:
                logger.debug("Form validation failed")

        else:
            form = form_cls(
                initial={
                    "pk": pk_list,
                    "return_url": self.get_return_url(request),
                }
            )

        # Retrieve objects being deleted
        table = self.table(self.queryset.filter(pk__in=pk_list), orderable=False)
        if not table.rows:
            messages.warning(
                request,
                "No {} were selected for deletion.".format(
                    model._meta.verbose_name_plural
                ),
            )
            return redirect(self.get_return_url(request))

        context = {
            "form": form,
            "obj_type_plural": model._meta.verbose_name_plural,
            "table": table,
            "return_url": self.get_return_url(request),
        }
        context.update(self.extra_context())
        return render(request, self.template_name, context)


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
        src, dest = kwargs["src"], kwargs["dest"]
        Branch.objects.get(name=dest).merge(src, user=req.user)
        messages.info(
            req, mark_safe(f"<h4>merged branch <b>{src}</b> into <b>{dest}</b></h4>")
        )
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
    template_name = "dolt/commit_list.html"
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
    queryset = PullRequest.objects.all().order_by("-created_at")
    filterset = filters.PullRequestFilterSet
    filterset_form = forms.PullRequestFilterForm
    table = tables.PullRequestTable
    # action_buttons = ("add",)  # todo: add button
    action_buttons = ()
    template_name = "dolt/pull_request_list.html"


class PullRequestBase(generic.ObjectView):
    queryset = PullRequest.objects.all()
    actions = ()

    def get_extra_context(self, req, obj, **kwargs):
        src, dest = obj.get_src_dest_branches()
        return {
            "counts": {
                "num_conflicts": merge.get_conflicts_count_for_merge(src, dest),
                "num_reviews": obj.num_reviews,
                "num_commits": obj.num_commits,
            }
        }


class PullRequestDiffView(PullRequestBase):
    template_name = "dolt/pull_request/diffs.html"

    def get_extra_context(self, req, obj, **kwargs):
        ctx = super().get_extra_context(req, obj, **kwargs)
        head = Branch.objects.get(name=obj.source_branch).hash
        merge_base = Commit.merge_base(obj.source_branch, obj.destination_branch)
        ctx.update(
            {
                "active_tab": "diffs",
                "results": diffs.two_dot_diffs(from_commit=merge_base, to_commit=head),
            }
        )
        return ctx


class PullRequestConflictView(PullRequestBase):
    template_name = "dolt/pull_request/conflicts.html"

    def get_extra_context(self, req, obj, **kwargs):
        ctx = super().get_extra_context(req, obj, **kwargs)
        src = Branch.objects.get(name=obj.source_branch)
        dest = Branch.objects.get(name=obj.destination_branch)
        ctx.update(
            {
                "active_tab": "conflicts",
                "conflicts": merge.get_conflicts_for_merge(src, dest),
            }
        )
        return ctx


class PullRequestReviewListView(PullRequestBase):
    template_name = "dolt/pull_request/review_list.html"

    def get_extra_context(self, req, obj, **kwargs):
        ctx = super().get_extra_context(req, obj, **kwargs)
        reviews = PullRequestReview.objects.filter(pull_request=obj.pk).order_by(
            "reviewed_at"
        )
        ctx.update(
            {
                "active_tab": "reviews",
                "review_list": reviews,
            }
        )
        return ctx


class PullRequestCommitListView(PullRequestBase):
    template_name = "dolt/pull_request/commits.html"
    table = tables.CommitTable

    def get_extra_context(self, req, obj, **kwargs):
        ctx = super().get_extra_context(req, obj, **kwargs)
        ctx.update(
            {
                "active_tab": "commits",
                "commit_list": self.table(obj.commits),
            }
        )
        return ctx


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

    def alter_obj(self, obj, request, url_args, url_kwargs):
        # Allow views to add extra info to an object before it is processed. For example, a parent object can be defined
        # given some parameter from the request URL.
        obj.creator = request.user
        return obj


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

    def get_return_url(self, req, obj):
        return reverse(
            "plugins:dolt:pull_request_reviews",
            kwargs={"pk": obj.pull_request.pk},
        )

    def alter_obj(self, obj, request, url_args, url_kwargs):
        obj.reviewer = request.user
        return obj

    def post(self, req, *args, **kwargs):
        kwargs["user"] = req.user
        return super().post(req, *args, **kwargs)


class PullRequestMergeView(generic.ObjectEditView):
    queryset = PullRequest.objects.all()
    form = ConfirmationForm()
    template_name = "dolt/pull_request/confirm_merge.html"

    def get(self, request, pk):
        pr = get_object_or_404(self.queryset, pk=pk)
        if pr.state != PullRequest.OPEN:
            msg = mark_safe(f"""Pull request "{pr}" is not open and cannot be merged""")
            messages.error(request, msg)
            return redirect("plugins:dolt:pull_request", pk=pr.pk)
        src = Branch.objects.get(name=pr.source_branch)
        dest = Branch.objects.get(name=pr.destination_branch)
        return render(
            request,
            self.template_name,
            {
                "pull_request": pr,
                "form": self.form,
                "return_url": pr.get_absolute_url(),
                "conflicts": merge.get_conflicts_for_merge(src, dest),
                "diffs": diffs.three_dot_diffs(from_commit=dest, to_commit=src),
            },
        )

    def post(self, request, pk):
        pr = get_object_or_404(self.queryset, pk=pk)
        form = ConfirmationForm(request.POST)

        if form.is_valid():
            pr.merge(user=request.user)
            messages.success(
                request,
                mark_safe(f"""Pull Request <strong>"{pr}"</strong> has been merged."""),
            )
            return redirect("plugins:dolt:pull_request", pk=pr.pk)

        return render(
            request,
            self.template_name,
            {
                "pull_request": pr,
                "form": self.form,
                "return_url": pr.get_absolute_url(),
            },
        )


class PullRequestCloseView(generic.ObjectEditView):
    queryset = PullRequest.objects.all()
    form = ConfirmationForm()
    template_name = "dolt/pull_request/confirm_close.html"

    def get(self, request, pk):
        pr = get_object_or_404(self.queryset, pk=pk)
        if pr.state != PullRequest.OPEN:
            msg = mark_safe(f"""Pull request "{pr}" is not open and cannot be closed""")
            messages.error(request, msg)
            return redirect("plugins:dolt:pull_request", pk=pr.pk)

        return render(
            request,
            self.template_name,
            {
                "pull_request": pr,
                "form": self.form,
                "panel_class": "default",
                "button_class": "primary",
                "return_url": pr.get_absolute_url(),
            },
        )

    def post(self, request, pk):
        pr = get_object_or_404(self.queryset, pk=pk)
        form = ConfirmationForm(request.POST)

        if form.is_valid():
            pr.state = PullRequest.CLOSED
            pr.save()
            msg = mark_safe(
                f"""<strong>Pull Request "{pr}" has been closed.</strong>"""
            )
            messages.success(request, msg)
            return redirect("plugins:dolt:pull_request", pk=pr.pk)

        return render(
            request,
            self.template_name,
            {
                "pull_request": pr,
                "form": self.form,
                "return_url": pr.get_absolute_url(),
            },
        )
