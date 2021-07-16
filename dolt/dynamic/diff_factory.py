import copy

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

import django_tables2 as tables
from django_tables2.utils import call_with_appropriate

from nautobot.utilities.querysets import RestrictedQuerySet
from nautobot.utilities.tables import BaseTable

from dolt.dynamic.model_view_map import MODEL_VIEW_TABLES


class DiffModelFactory:
    def __init__(self, content_type):
        self.content_type = content_type

    def get_model(self):
        try:
            return apps.get_model("dolt", self.model_name)
        except LookupError:
            return self.make_model()

    def make_model(self):
        props = {
            "__module__": "dolt.models",
            "_declared": timezone.now(),
            "Meta": self._model_meta(),
            "objects": RestrictedQuerySet.as_manager(),
            **self._make_diff_fields(),
        }
        model = type(self.model_name, (models.Model,), props)
        for f in model._meta.get_fields():
            # back-link field references
            f.model = model
        return model

    def _model_meta(self):
        class Meta:
            app_label = "dolt"
            managed = False
            db_table = self.diff_table_name
            verbose_name = self.model_name

        return Meta

    @property
    def model_name(self):
        return f"diff_{self.content_type.model}"

    @property
    def source_model_verbose_name(self):
        return str(self.content_type.model_class()._meta.verbose_name.capitalize())

    @property
    def diff_table_name(self):
        return (
            f"dolt_commit_diff_{self.content_type.app_label}_{self.content_type.model}"
        )

    @property
    def _model_fields(self):
        return self.content_type.model_class()._meta.get_fields()

    def _make_diff_fields(self):
        diff_fields = [
            models.SlugField(name="to_commit"),
            models.DateTimeField(name="to_commit_date"),
            models.SlugField(name="from_commit"),
            models.DateTimeField(name="from_commit_date"),
            models.SlugField(name="diff_type"),
        ]

        for field in self._model_fields:
            if not field.concrete or field.is_relation:
                continue
            diff_fields.extend(self._diff_fields_from_field(field))
        return {df.name: df for df in diff_fields}

    def _diff_fields_from_field(self, field):
        def clone_field(prefix):
            field_type = type(field)
            kwargs = {"name": f"{prefix}{field.name}"}

            # copy these kwargs if they exist
            optional = ("primary_key", "target_field", "base_field")
            for kw in optional:
                if kw in field.__dict__:
                    kwargs[kw] = field.__dict__[kw]
            return field_type(**kwargs)

        return [clone_field(pre) for pre in ("to_", "from_")]


class DiffListViewFactory:
    def __init__(self, content_type):
        self.ct = content_type

    def get_table_model(self):
        try:
            return apps.get_model("dolt", self.table_model_name)
        except LookupError:
            return self.make_table_model()

    def make_table_model(self):
        try:
            ModelViewTable = MODEL_VIEW_TABLES[self.ct.app_label][self.ct.model]

            return type(
                self.table_model_name,
                (
                    ModelViewTable,
                    DiffListViewBase,
                ),
                {
                    "__module__": "dolt.tables",
                    "_declared": timezone.now(),
                    "Meta": self._get_table_meta(ModelViewTable),
                    "content_type": self.ct,
                },
            )
        except KeyError as e:
            raise e

    def _get_table_meta(self, table):
        meta = copy.deepcopy(table._meta)
        # add diff styling
        meta.row_attrs = {"class": row_attrs_for_record}
        meta.sequence = ("diff", "...")
        return meta

    @property
    def table_model_name(self):
        return f"diff_{str(self.ct.app_label)}_{str(self.ct.model)}"


def row_attrs_for_record(record):
    if record.diff["diff_type"] == "added":
        return "bg-success"
    if record.diff["diff_type"] == "removed":
        return "bg-danger"

    # diff_type == "modified"
    if record.diff["root"] == "to":
        return "bg-warning"
    if record.diff["root"] == "from":
        return "bg-warning"


class DiffListViewBase(tables.Table):
    diff = tables.Column(verbose_name="Diff Type")

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for col in self.columns:
            if col.name == "diff":
                continue  # uses `render_diff()`
            col.render = self.wrap_render_func(col.render)

    def render_diff(self, value, record):
        """
        Custom rendering for the the `Diff Type` columns
        """
        ct = ContentType.objects.get_for_model(self.Meta.model)
        href = reverse(
            "plugins:dolt:diff_detail",
            kwargs={
                "app_label": ct.app_label,
                "model": ct.model,
                "from_commit": record.diff["from_commit"],
                "to_commit": record.diff["to_commit"],
                "pk": record.pk,
            },
        )

        if record.diff["diff_type"] == "added":
            return format_html(
                f"""<a href="{ href }">
                    <span class="label label-success">added</span>
                </a>"""
            )
        elif record.diff["diff_type"] == "removed":
            return format_html(
                f"""<a href="{ href }">
                    <span class="label label-danger">removed</span>
                </a>"""
            )
        else:  # diff_type == "modified"
            cnt = self.count_diffs(record.diff)
            return format_html(
                f"""<a href="{ href }">
                    <span class="label label-primary">changed ({ cnt })</span>
                </a>"""
            )

    @staticmethod
    def count_diffs(diff):
        skip_fields = (
            "root",
            "diff_type",
            "to_commit",
            "to_commit_date",
            "from_commit",
            "from_commit_date",
        )
        cnt = 0
        for k, v in diff.items():
            if k in skip_fields:
                continue
            if k.startswith("to_"):
                # compare to and from values
                from_key = f"from_{k[3:]}"
                if v != diff[from_key]:
                    cnt += 1
        return cnt

    @staticmethod
    def wrap_render_func(fn):
        """
        Wraps an existing cell rendering function with diff styling
        """

        def render_before_after_diff(
            value, record, column, bound_column, bound_row, table
        ):
            # the previous render function may take any of the
            # following args, so provide them all
            kwargs = {
                "value": value,
                "record": record,
                "column": column,
                "bound_column": bound_column,
                "bound_row": bound_row,
                "table": table,
            }
            # render using the existing function
            cell = call_with_appropriate(fn, kwargs)

            if record.diff["diff_type"] != "modified":
                # only render before/after diff styling
                # for 'modified' rows
                return cell

            before_name = f"from_{bound_column.name}"
            if before_name not in record.diff:
                # can't render diff styling
                return cell

            # re-render the cell value with its before value
            kwargs["value"] = record.diff[before_name]
            before_cell = call_with_appropriate(fn, kwargs)

            if before_cell == cell:
                # no change
                return cell

            before_cell = before_cell if before_cell else " — "
            return format_html(
                f"""<div>
                <span class="bg-danger text-danger">
                    <b>{before_cell}</b>
                </span>
                </br>
                <span class="bg-success text-success">
                    <b>{cell}</b>
                </span>
            </div>"""
            )

        return render_before_after_diff
