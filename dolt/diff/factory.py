import copy

from django.apps import apps
from django.db import models
from django.utils import timezone
import django_tables2 as tables

from nautobot.utilities.querysets import RestrictedQuerySet
from nautobot.utilities.tables import BaseTable

from dolt.diff.view_tables import MODEL_VIEW_TABLES


class OldDiffModelFactory:
    def __init__(self, content_type):
        self.ct = content_type

    def get_model(self):
        try:
            return apps.get_model("dolt", self.model_name)
        except LookupError:
            return self.make_model()

    def get_table_model(self):
        try:
            return apps.get_model("dolt", self.table_model_name)
        except LookupError:
            return self.make_table_model()

    @property
    def model_name(self):
        return f"diff_{self.ct.model}"

    @property
    def table_model_name(self):
        return f"diff_{self.ct.model}_table"

    def make_model(self):
        fields = {df.name: df for df in self._get_diffable_fields()}
        props = {
            "__module__": "dolt.models",
            "_declared": timezone.now(),
            "Meta": self._model_meta(),
            "objects": RestrictedQuerySet.as_manager(),
            **fields,
        }
        return type(self.model_name, (models.Model,), props)

    def make_table_model(self):
        meta = self._table_model_meta(self.get_model())
        props = {
            "__module__": "dolt.tables",
            "_declared": timezone.now(),
            "Meta": meta,
        }
        return type(self.table_model_name, (BaseTable,), props)

    def _model_meta(self):
        class Meta:
            app_label = "dolt"
            managed = False
            db_table = self.db_view_name
            verbose_name = self.model_name

        return Meta

    def _table_model_meta(self, diff_model):
        class Meta(BaseTable.Meta):
            model = diff_model
            fields = [f.name for f in self._get_diffable_fields()]
            default_columns = [f.name for f in self._get_diffable_fields()]
            row_attrs = {
                "class": lambda record: {
                    "added": "bg-success",
                    "removed": "bg-danger",
                    "before": "bg-warning",
                    "after": "bg-warning",
                }[record.change_type],
            }

        return Meta

    def _get_diffable_fields(self):
        return [
            models.TextField(name="dolt_commit"),
            models.TextField(name="change_type"),
        ] + self._clone_src_fields()

    def _clone_src_fields(self):
        fields = []
        for f in self._src_model_fields:
            if f.concrete and not f.is_relation and not f.blank:
                fields.append(self._clone_field(f))
        return fields

    @staticmethod
    def _clone_field(field):
        kws = (
            "name",
            "base_field",
        )
        kwargs = {}

        for kw in kws:
            if kw in field.__dict__:
                kwargs[kw] = field.__dict__[kw]

        return type(field)(**kwargs)

    @property
    def _src_model_fields(self):
        return self.ct.model_class()._meta.get_fields()

    @property
    def _src_model_pk(self):
        return self.ct.model_class()._meta.pk.name

    @property
    def db_view_name(self):
        return f"vcs_diff_{self.ct.app_label}_{self.ct.model}"

    @property
    def db_diff_table_name(self):
        return f"dolt_diff_{self.ct.app_label}_{self.ct.model}"

    def db_view_definition(self):
        to_fields = [f"to_{f.name} as {f.name}" for f in self._clone_src_fields()]
        from_fields = [f"from_{f.name} as {f.name}" for f in self._clone_src_fields()]
        return f"""
        CREATE VIEW {self.db_view_name} AS (
            SELECT
                to_commit as dolt_commit,
                REPLACE(diff_type, "modified", "after") as change_type,
                {", ".join(to_fields)}
            FROM
                {self.db_diff_table_name }
            WHERE {self._src_model_pk} IS NOT NULL
        ) UNION (
            SELECT
                from_commit as dolt_commit,
                REPLACE(diff_type, "modified", "before") as change_type,
                {", ".join(from_fields)}
            FROM
                 {self.db_diff_table_name }
            WHERE {self._src_model_pk} IS NOT NULL
        );"""


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
            db_table = self._dolt_diff_table_name
            verbose_name = self.model_name

        return Meta

    @property
    def model_name(self):
        return f"diff_{self.content_type.model}"

    @property
    def _dolt_diff_table_name(self):
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
            for opt in ("target_field",):
                if opt in field.__dict__:
                    kwargs[opt] = field.__dict__[opt]
            try:
                return field_type(**kwargs)
            except TypeError as e:
                breakpoint()
                pass

        return [clone_field(pre) for pre in ("to_", "from_")]


class DiffViewTableFactory:
    def __init__(self, content_type):
        self.ct = content_type

    def get_table_model(self):
        try:
            return apps.get_model("dolt", self.table_model_name)
        except LookupError:
            return self.make_table_model()

    def make_table_model(self):
        try:
            ModelViewTable = MODEL_VIEW_TABLES[str(self.ct)]

            return type(
                self.table_model_name,
                (ModelViewTable,),
                {
                    "__module__": "dolt.tables",
                    "_declared": timezone.now(),
                    "Meta": self._get_table_meta(ModelViewTable),
                },
            )
        except KeyError as e:
            raise e

    def _get_table_meta(self, table):
        meta = table._meta
        # add diff styling
        meta.row_attrs = {
            "class": lambda record: {
                "added": "bg-success",
                "removed": "bg-danger",
                "before": "bg-warning",
                "after": "bg-warning",
            }[record.diff_type],
        }
        return meta

    @property
    def table_model_name(self):
        return f"{str(self.ct)}_diff_table"

    @staticmethod
    def has_diff_table(content_type):
        return str(content_type) in MODEL_VIEW_TABLES
