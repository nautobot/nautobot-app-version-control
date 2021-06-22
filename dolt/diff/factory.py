import copy

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
import django_tables2 as tables

from nautobot.utilities.querysets import RestrictedQuerySet
from nautobot.utilities.tables import BaseTable

from dolt.diff.model_view_map import MODEL_VIEW_TABLES


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

            for opt in ("primary_key", "target_field", "base_field"):
                if opt in field.__dict__:
                    kwargs[opt] = field.__dict__[opt]
            try:
                return field_type(**kwargs)
            except TypeError as e:
                breakpoint()
                pass

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
        meta.row_attrs = {
            "class": lambda record: {
                "added": "bg-success",
                "removed": "bg-danger",
                "modified": "bg-warning",
                # None: None,
            }[record.diff_type],
        }
        meta.sequence = ("diff_type", "...")
        return meta

    @property
    def table_model_name(self):
        return f"diff_{str(self.ct.app_label)}_{str(self.ct.model)}"


class DiffListViewBase(tables.Table):
    diff_type = tables.Column()

    def render_diff_type(self, value, record):
        href = self.diff_detail_link(record)
        if record.diff_type == "added":
            return format_html(
                f"""<a href="{ href }">
                    <span class="label label-success">added</span>
                </a>"""
            )
        if record.diff_type == "removed":
            return format_html(
                f"""<a href="{ href }">
                    <span class="label label-danger">removed</span>
                </a>"""
            )

        # diff_type == "modified"
        if record.diff_root == "to":
            return format_html(
                f"""<a href="{ href }">
                    <span class="label label-primary">changed</span>
                    </br>
                    <span class="label label-success">after</span>
                </a>"""
            )
        if record.diff_root == "from":
            return format_html(
                f"""<a href="{ href }">
                    <span class="label label-primary">changed</span>
                    </br>
                    <span class="label label-danger">before</span>
                </a>"""
            )

    def diff_detail_link(self, record):
        ct = ContentType.objects.get_for_model(self.Meta.model)
        return reverse(
            "plugins:dolt:diff_detail",
            kwargs={
                "app_label": ct.app_label,
                "model": ct.model,
                "from_commit": record.from_commit,
                "to_commit": record.to_commit,
                "pk": record.pk,
            },
        )

    class Meta:
        abstract = True
