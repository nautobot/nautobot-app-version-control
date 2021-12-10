"""views.py implements django views for all Version Control plugin features."""

from datetime import datetime
import logging

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, get_list_or_404, render, redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views import View

from nautobot.core.views import generic
from nautobot.dcim.models.sites import Site
from nautobot.utilities.forms import ConfirmationForm
from nautobot.utilities.permissions import get_permission_for_model
from nautobot.utilities.views import GetReturnURLMixin, ObjectPermissionRequiredMixin

from nautobot_version_control import diffs, filters, forms, merge, tables
from nautobot_version_control.constants import DOLT_DEFAULT_BRANCH
from nautobot_version_control.utils import alter_session_branch, db_for_commit, active_branch
from nautobot_version_control.models import (
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
    """BranchView renders a view of a Branch object."""

    queryset = Branch.objects.all()

    def get_extra_context(self, request, instance):  # pylint: disable=W0613,C0116 # noqa: D102
        merge_base = Commit.merge_base(DOLT_DEFAULT_BRANCH, instance.name)
        head = instance.hash
        return {"results": diffs.two_dot_diffs(from_commit=merge_base, to_commit=head)}


class BranchListView(generic.ObjectListView):
    """BranchListView renders a view of all branches."""

    queryset = Branch.objects.exclude(name__startswith="xxx")
    filterset = filters.BranchFilterSet
    filterset_form = forms.BranchFilterForm
    table = tables.BranchTable
    action_buttons = ("add",)
    template_name = "nautobot_version_control/branch_list.html"

    def extra_context(self):  # pylint: disable=W0613,C0116  # noqa: D102
        return {"default_branch": DOLT_DEFAULT_BRANCH}


class BranchCheckoutView(View):
    """BranchCheckoutView renders a view of checking out a branch."""

    queryset = Branch.objects.all()
    model_form = forms.BranchForm
    template_name = "nautobot_version_control/branch_edit.html"

    def get(self, req, *args, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        # new branch will be checked out on redirect
        alter_session_branch(sess=req.session, branch=kwargs["pk"])
        return redirect("/")


class BranchEditView(generic.ObjectEditView):
    """BranchEditView renders either an add or create a branch."""

    queryset = Branch.objects.all()
    model_form = forms.BranchForm
    template_name = "nautobot_version_control/branch_edit.html"

    def get(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        initial = {
            "starting_branch": Branch.objects.get(name=DOLT_DEFAULT_BRANCH),
            "creator": request.user,
        }
        return render(
            request,
            self.template_name,
            {
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": self.model_form(initial=initial),
            },
        )

    def post(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116  # noqa: D102
        form = self.model_form(data=request.POST, files=request.FILES)
        response = super().post(request, *args, **kwargs)
        if BranchEditView._is_success_response(response):
            self.create_branch_meta(request, form)
            alter_session_branch(sess=request.session, branch=form.data.get("name"))
        return response

    @staticmethod
    def _is_success_response(response):
        """returns if response was successful."""
        return response.status_code // 100 in (2, 3)

    @staticmethod
    def create_branch_meta(req, form):
        """creates a BranchMeta object for a Branch."""
        meta, _ = BranchMeta.objects.get_or_create(branch=form.data.get("name"))
        meta.source_branch = form.data.get("starting_branch")
        meta.author = req.user
        meta.created = datetime.now()
        meta.save()


class BranchBulkEditView(generic.BulkEditView):
    """BranchBulkEditView is used to edit a set of branches at once."""

    queryset = Branch.objects.all()
    filterset = filters.BranchFilterSet
    table = tables.BranchTable
    form = forms.BranchBulkEditForm


class BranchBulkDeleteView(generic.BulkDeleteView):
    """BranchBulkDeleteView is used to delete a set of branches at once."""

    queryset = Branch.objects.all()
    table = tables.BranchTable
    form = forms.BranchBulkDeleteForm
    template_name = "nautobot_version_control/branch_bulk_delete.html"

    def get(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        return redirect(self.get_return_url(request))

    def post(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116  # noqa: D102
        logger = logging.getLogger("nautobot.views.BulkDeleteView")
        model = self.queryset.model

        # Are we deleting *all* objects in the queryset or just a selected subset?
        if request.POST.get("_all"):
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
                except Exception as e:
                    logger.info("Caught error while attempting to delete objects")
                    messages.error(request, mark_safe(e))
                    return redirect(self.get_return_url(request))

                msg = f"Deleted {deleted_count} {model._meta.verbose_name_plural}"
                logger.info(msg)
                messages.success(request, msg)
                return redirect(self.get_return_url(request))

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
            messages.warning(request, f"No {model._meta.verbose_name_plural} were selected for deletion.")
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
    """BranchMergeFormView is used to confirm a merge."""

    queryset = Branch.objects.all()
    form = forms.MergeForm
    template_name = "nautobot_version_control/branch_merge.html"

    def get(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        initial = {
            # TODO: use branch meta source branch
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

    def post(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116  # noqa: D102
        form = self.form(data=request.POST, files=request.FILES)
        if not form.is_valid():
            raise ValueError(form.errors)
        src = form.cleaned_data.get("source_branch")
        dest = form.cleaned_data.get("destination_branch")
        # todo: don't use redirect
        return redirect(
            reverse(
                "plugins:nautobot_version_control:branch_merge_preview",
                kwargs={"src": src, "dest": dest},
            )
        )


class BranchMergePreView(GetReturnURLMixin, View):
    """BranchMergePreView is used to render a preview of a merge."""

    queryset = Branch.objects.all()
    form = forms.MergePreviewForm
    template_name = "nautobot_version_control/branch_merge_preview.html"

    def get(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        src = Branch.objects.get(name=kwargs["src"])
        dest = Branch.objects.get(name=kwargs["dest"])
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
                **self.get_extra_context(request, src, dest),
            },
        )

    def post(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        src, dest = kwargs["src"], kwargs["dest"]
        Branch.objects.get(name=dest).merge(src, user=request.user)
        messages.info(request, mark_safe(f"<h4>merged branch <b>{src}</b> into <b>{dest}</b></h4>"))
        alter_session_branch(sess=request.session, branch=dest)
        return redirect("/")

    def get_extra_context(self, request, src, dest):  # pylint: disable=W0613,C0116,R0201 # noqa: D102
        merge_base_c = Commit.merge_base(src, dest)
        source_head = src.hash
        return {
            "results": diffs.two_dot_diffs(from_commit=merge_base_c, to_commit=source_head),
            "conflicts": merge.get_conflicts_for_merge(src, dest),
            "back_btn_url": reverse("plugins:nautobot_version_control:branch_merge", args=[src.name]),
        }


#
# Commits
#


class CommitView(generic.ObjectView):
    """CommitView is used to render a commit."""

    queryset = Commit.objects.all()

    def get(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
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
    """CommitListView is used to a render a list of Commits."""

    queryset = Commit.objects.all()
    filterset = filters.CommitFilterSet
    filterset_form = forms.CommitFilterForm
    table = tables.CommitTable
    template_name = "nautobot_version_control/commit_list.html"
    action_buttons = None

    def alter_queryset(self, request):  # noqa: D102
        if active_branch() != DOLT_DEFAULT_BRANCH:
            # only list commits on the current branch since the merge-base
            merge_base_hash = Commit.merge_base(DOLT_DEFAULT_BRANCH, active_branch())
            merge_base = Commit.objects.get(commit_hash=merge_base_hash)
            self.queryset = self.queryset.filter(date__gt=merge_base.date)
        return self.queryset

    def extra_context(self):  # pylint: disable=W0613,C0116 # noqa: D102
        return {"active_branch": active_branch()}


class CommitEditView(generic.ObjectEditView):
    """CommitEditView is used to edit a commit."""

    queryset = Commit.objects.all()
    model_form = forms.CommitForm
    template_name = "nautobot_version_control/commit_edit.html"


class CommitDeleteView(generic.ObjectDeleteView):
    """CommitDeleteView is used to render the deletion of a commit."""

    queryset = Commit.objects.all()


class CommitRevertView(GetReturnURLMixin, ObjectPermissionRequiredMixin, View):
    """Revert Commits in bulk."""

    queryset = Commit.objects.all()
    form = forms.CommitBulkRevertForm
    table = tables.CommitRevertTable
    template_name = "nautobot_version_control/commit_revert.html"

    def get_required_permission(self):  # noqa: D102
        return get_permission_for_model(self.queryset.model, "change")

    def get_return_url(self, req):  # pylint: disable=W0221,W0613 # noqa: D102
        return reverse("plugins:nautobot_version_control:commit_list")

    def post(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        model = self.queryset.model
        pk_list = request.POST.getlist("pk")
        commits = self.queryset.filter(commit_hash__in=pk_list)

        if commits.count() != len(pk_list):
            found = set([c.commit_hash for c in commits])  # pylint: disable=R1718
            missing = [f"<strong>{h}</strong>" for h in pk_list if h not in found]
            messages.warning(
                request,
                mark_safe(
                    f"""Cannot revert commit(s) {", ".join(missing)},
                        commits were not found on branch
                        <strong>{active_branch()}</strong>"""
                ),
            )
            return redirect(self.get_return_url(request))

        context = {
            "pk": pk_list,
            "active_branch": active_branch(),
            "obj_type_plural": model._meta.verbose_name_plural,
            "content_type": ContentType.objects.get_for_model(model),
            "return_url": self.get_return_url(request),
        }

        if "_revert" in request.POST:
            context.update(
                {
                    "form": self.form(initial={"pk": pk_list}),
                    "table": self.table(commits),
                }
            )
            return render(request, self.template_name, context)

        if "_confirm" in request.POST:
            form = self.form(request.POST)
            if form.is_valid():
                commits = form.cleaned_data["pk"]
                msgs = [f"""<strong>"{c.short_message}"</strong>""" for c in commits]
                try:
                    _ = Commit.revert(commits, request.user)
                except Exception as e:
                    # catch database error
                    messages.error(
                        request,
                        mark_safe(f"""Error reverting commits {", ".join(msgs)}: {e}"""),
                    )
                    return redirect(self.get_return_url(request))
                else:
                    messages.success(
                        request,
                        mark_safe(f"""Successfully reverted commits {", ".join(msgs)}"""),
                    )

        return redirect(self.get_return_url(request))


#
# Diffs
#


class ActiveBranchDiffs(View):
    """ActiveBranchDiffs is used to render the differences in the current active_branch."""

    def get(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        return redirect(
            reverse(
                "plugins:nautobot_version_control:branch",
                kwargs={
                    "pk": active_branch(),
                },
            )
        )


class DiffDetailView(View):
    """DiffDetailView is used to render complex diff between a from and to commit."""

    template_name = "nautobot_version_control/diff_detail.html"

    def get_required_permission(self):  # pylint: disable=R0201
        """returns permissions."""
        return get_permission_for_model(Site, "view")

    def get(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        self.model = self.get_model(kwargs)  # pylint: disable=W0201
        before_obj, after_obj = self.get_objs(kwargs)
        return render(
            request,
            self.template_name,
            {
                "title": self.title(before_obj, after_obj),
                "display_name": self.display_name(kwargs),
                "diff_obj": self.get_json_diff(before_obj, after_obj),
                **self.breadcrumb(kwargs),
            },
        )

    def get_model(self, kwargs):
        """get_model returns the underlying model."""
        return ContentType.objects.get(app_label=kwargs["app_label"], model=kwargs["model"]).model_class()

    @staticmethod
    def title(before_obj, after_obj):
        """title returns the title of a diff."""
        if before_obj and after_obj:
            return f"Updated {after_obj}"
        elif after_obj:
            return f"Added {after_obj}"
        else:
            return f"Deleted {before_obj}"

    def breadcrumb(self, kwargs):
        """Return a breadcrumb."""
        return {
            "breadcrumb": {
                "app_label": kwargs["app_label"],
                "model": self.display_name(kwargs),
                "from": self.match_commit(kwargs["from_commit"]),
                "to": self.match_commit(kwargs["to_commit"]),
            }
        }

    @staticmethod
    def match_commit(commit):
        """Replace `commit` with a more semantically meaningful identifier, if possible."""
        if Branch.objects.filter(hash=str(commit)).count() == 1:
            b = Branch.objects.get(hash=str(commit))
            url = b.get_absolute_url()
            return mark_safe(f"<a href='{url}'>{b}</a>")
        elif Commit.objects.filter(commit_hash=str(commit)).exists():
            c = Commit.objects.get(commit_hash=str(commit))
            url = c.get_absolute_url()
            return mark_safe(f"<a href='{url}'>{c}</a>")
        return commit

    def display_name(self, kwargs):
        """returns the verbose name of the model."""
        return self.get_model(kwargs)._meta.verbose_name.capitalize()

    def get_objs(self, kwargs):
        """Returns the commit objects for the before and after of a diff."""
        pk = kwargs["pk"]
        from_commit = kwargs["from_commit"]
        to_commit = kwargs["to_commit"]
        qs = self.model.objects.all()
        before_obj, after_obj = None, None

        from_qs = qs.using(db_for_commit(from_commit))
        if from_qs.filter(pk=pk).exists():
            before_obj = from_qs.get(pk=pk)
        to_qs = qs.using(db_for_commit(to_commit))
        if to_qs.filter(pk=pk).exists():
            after_obj = to_qs.get(pk=pk)
        return before_obj, after_obj

    def get_json_diff(self, before_obj, after_obj):
        """Returns the diff as json objs."""
        before_obj = self.serialize_obj(before_obj)
        after_obj = self.serialize_obj(after_obj)
        added = not before_obj
        removed = not after_obj

        json_diff = []
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

                json_diff.append(
                    {
                        "name": field,
                        "before_val": before_val,
                        "before_style": before_style,
                        "after_val": after_val,
                        "after_style": after_style,
                    }
                )

        return json_diff

    def serialize_obj(self, obj):
        """serialize_obj converts a model into a json object."""
        if not obj:
            return {}
        json_obj = {}
        fields = {f.name for f in obj._meta.fields}
        fields |= set(self.model.csv_headers)
        for field in fields:
            try:
                val = getattr(obj, field)
                val = str(val) if val else "-"
                json_obj[field] = val
            except AttributeError:
                continue
        return json_obj


#
# Pull Requests
#


class PullRequestListView(generic.ObjectListView):
    """PullRequestListView is used to render a lit of pull requests."""

    queryset = PullRequest.objects.all().order_by("-created_at")
    filterset = filters.PullRequestDefaultOpenFilterSet
    filterset_form = forms.PullRequestFilterForm
    table = tables.PullRequestTable
    action_buttons = ()
    template_name = "nautobot_version_control/pull_request_list.html"


class PullRequestBase(generic.ObjectView):
    """PullRequestBase contains the base information about a PullRequest."""

    queryset = PullRequest.objects.all()
    actions = ()

    def get_extra_context(self, request, obj, **kwargs):  # pylint: disable=W0613,C0116,W0237 # noqa: D102
        src, dest = obj.get_src_dest_branches()
        return {
            "counts": {
                "num_conflicts": merge.get_conflicts_count_for_merge(src, dest),
                "num_reviews": obj.num_reviews,
                "num_commits": obj.num_commits,
            }
        }


class PullRequestDiffView(PullRequestBase):
    """PullRequestDiffView displays a diff for a pull request."""

    template_name = "nautobot_version_control/pull_request/diffs.html"

    def get_extra_context(self, request, obj, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        ctx = super().get_extra_context(request, obj, **kwargs)
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
    """PullRequestConflictView renders a conflict for a pull request."""

    template_name = "nautobot_version_control/pull_request/conflicts.html"

    def get_extra_context(self, request, obj, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        ctx = super().get_extra_context(request, obj, **kwargs)
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
    """PullRequestReviewListView renders a list of pull requests."""

    template_name = "nautobot_version_control/pull_request/review_list.html"

    def get_extra_context(self, request, obj, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        ctx = super().get_extra_context(request, obj, **kwargs)
        reviews = PullRequestReview.objects.filter(pull_request=obj.pk).order_by("reviewed_at")
        ctx.update(
            {
                "active_tab": "reviews",
                "review_list": reviews,
            }
        )
        return ctx


class PullRequestCommitListView(PullRequestBase):
    """PullRequestCommitListView renders a list of commits."""

    template_name = "nautobot_version_control/pull_request/commits.html"
    table = tables.CommitTable

    def get_extra_context(self, request, obj, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        ctx = super().get_extra_context(request, obj, **kwargs)
        ctx.update(
            {
                "active_tab": "commits",
                "commits_table": self.table(obj.commits),
            }
        )
        return ctx


class PullRequestEditView(generic.ObjectEditView):
    """PullRequestEditView renders an edit view for a PR."""

    queryset = PullRequest.objects.all()
    model_form = forms.PullRequestForm
    template_name = "nautobot_version_control/pull_request/edit.html"

    def get(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        obj = self.get_object(kwargs)
        initial = {
            "destination_branch": Branch.objects.get(name=DOLT_DEFAULT_BRANCH),
            "source_branch": active_branch(),
        }

        if obj.present_in_database:
            initial["title"] = obj.title
            initial["source_branch"] = obj.source_branch
            initial["destination_branch"] = obj.destination_branch
            initial["description"] = obj.description

        # overwrite with any query strings
        query_string_source = request.GET.get("source_branch", "")
        if query_string_source != "":
            initial["source_branch"] = query_string_source

        query_string_destination = request.GET.get("destination_branch", "")
        if query_string_destination != "":
            initial["destination_branch"] = query_string_destination

        return render(
            request,
            self.template_name,
            {
                "obj": obj,
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": self.model_form(initial=initial),
                "return_url": self.get_return_url(request, obj),
                "editing": obj.present_in_database,
            },
        )

    def alter_obj(self, obj, request, url_args, url_kwargs):  # noqa: D102
        # Allow views to add extra info to an object before it is processed. For example, a parent object can be defined
        # given some parameter from the request URL.
        obj.creator = request.user
        return obj


class PullRequestReviewEditView(generic.ObjectEditView):
    """PullRequestReviewEditView renders an edit view for a PullRequestReview."""

    queryset = PullRequestReview.objects.all()
    model_form = forms.PullRequestReviewForm
    template_name = "nautobot_version_control/pull_request/review_edit.html"

    def get(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        initial = {
            "pull_request": PullRequest.objects.get(pk=kwargs["pull_request"]),
        }
        return render(
            request,
            self.template_name,
            {
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": self.model_form(initial=initial),
            },
        )

    def get_return_url(self, req, obj):  # pylint: disable=W0613,W0237 # noqa: D102
        return reverse(
            "plugins:nautobot_version_control:pull_request_reviews",
            kwargs={"pk": obj.pull_request.pk},
        )

    def alter_obj(self, obj, request, url_args, url_kwargs):  # noqa: D102
        obj.reviewer = request.user
        return obj

    def post(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        kwargs["user"] = request.user
        return super().post(request, *args, **kwargs)


class PullRequestMergeView(generic.ObjectEditView):
    """PullRequestMergeView renders a view for rendering a pull request review."""

    queryset = PullRequest.objects.all()
    form = ConfirmationForm()
    template_name = "nautobot_version_control/pull_request/confirm_merge.html"

    def get(self, request, pk):  # pylint: disable=W0613,C0116,W0221 # noqa: D102
        pr = get_object_or_404(self.queryset, pk=pk)
        if pr.state != PullRequest.OPEN:
            msg = mark_safe(f"""Pull request "{pr}" is not open and cannot be merged""")
            messages.error(request, msg)
            return redirect("plugins:nautobot_version_control:pull_request", pk=pr.pk)
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
                "diffs": diffs.three_dot_diffs(from_commit=dest.hash, to_commit=src.hash),
            },
        )

    def post(self, request, pk):  # pylint: disable=W0613,C0116,W0221 # noqa: D102
        pr = get_object_or_404(self.queryset, pk=pk)
        form = ConfirmationForm(request.POST)
        squash_param = request.POST.get("merge_squash", False)
        if squash_param == "true":
            squash_param = True

        if form.is_valid():
            pr.merge(user=request.user, squash=squash_param)
            messages.success(
                request,
                mark_safe(f"""Pull Request <strong>"{pr}"</strong> has been merged."""),
            )
            return redirect("plugins:nautobot_version_control:pull_request", pk=pr.pk)

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
    """PullRequestCloseView renders a view for closing a pr."""

    queryset = PullRequest.objects.all()
    form = ConfirmationForm()
    template_name = "nautobot_version_control/pull_request/confirm_close.html"

    def get(self, request, pk):  # pylint: disable=W0613,C0116,W0221 # noqa: D102
        pr = get_object_or_404(self.queryset, pk=pk)
        if pr.state != PullRequest.OPEN:
            msg = mark_safe(f"""Pull request "{pr}" is not open and cannot be closed""")
            messages.error(request, msg)
            return redirect("plugins:nautobot_version_control:pull_request", pk=pr.pk)

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

    def post(self, request, pk):  # pylint: disable=W0221 # noqa: D102
        pr = get_object_or_404(self.queryset, pk=pk)
        form = ConfirmationForm(request.POST)

        if form.is_valid():
            pr.state = PullRequest.CLOSED
            pr.save()
            msg = mark_safe(f"""<strong>Pull Request "{pr}" has been closed.</strong>""")
            messages.success(request, msg)
            return redirect("plugins:nautobot_version_control:pull_request", pk=pr.pk)

        return render(
            request,
            self.template_name,
            {
                "pull_request": pr,
                "form": self.form,
                "return_url": pr.get_absolute_url(),
            },
        )


class PullRequestBulkDeleteView(generic.BulkDeleteView):
    """PullRequestBulkDeleteView renders a bulk delete form for a list of pull requests."""

    queryset = PullRequest.objects.all()
    table = tables.PullRequestTable
    form = forms.PullRequestDeleteForm
    template_name = "nautobot_version_control/pull_request_bulk_delete.html"

    def get(self, request):  # pylint: disable=W0613,C0116 # noqa: D102
        return redirect(self.get_return_url(request))

    def post(self, request, *args, **kwargs):  # pylint: disable=W0613,C0116 # noqa: D102
        logger = logging.getLogger("nautobot.views.BulkDeleteView")
        model = self.queryset.model

        # Are we deleting *all* objects in the queryset or just a selected subset?
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
                except Exception:
                    logger.info("Caught error while attempting to delete objects")
                    return redirect(self.get_return_url(request))

                msg = f"Deleted {deleted_count} {model._meta.verbose_name_plural}"
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
                f"No {model._meta.verbose_name_plural} were selected for deletion.",
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
