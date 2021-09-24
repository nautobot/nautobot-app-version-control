""" conflict_factory.py is used to define the ConflictModelFactory that generates queryable Conflicts """

from django.apps import apps
from django.db import models
from django.utils import timezone

from nautobot.utilities.querysets import RestrictedQuerySet


class ConflictModelFactory:
    """
    ConflictModelFactory is used to represent a conflict between a particular model
    """

    def __init__(self, content_type):
        self.content_type = content_type

    def get_model(self):
        """ get_model returns the model we are querying conflicts for """

        try:
            return apps.get_model("dolt", self.model_name)
        except LookupError:
            return self.make_model()

    def make_model(self):
        """ Create a ConflicTModels for a model """
        props = {
            "__module__": "dolt.models",
            "_declared": timezone.now(),
            "Meta": self._model_meta(),
            "objects": RestrictedQuerySet.as_manager(),
            **self._make_conflict_fields(),
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
            db_table = self.conflict_table_name
            verbose_name = self.model_name

        return Meta

    @property
    def model_name(self):
        """ returns the model's name """
        return f"{self.content_type.model}_conflicts"

    @property
    def source_model_verbose_name(self):
        """ source_model_verbose_name returns the base model's verbose name """
        return str(self.content_type.model_class()._meta.verbose_name.capitalize())

    @property
    def conflict_table_name(self):
        """ returns the name of the model conflict table we are wrapping """
        return f"dolt_conflicts_{self.content_type.app_label}_{self.content_type.model}"

    @property
    def _model_fields(self):
        return self.content_type.model_class()._meta.get_fields()

    def _make_conflict_fields(self):
        conflict_fields = []
        for field in self._model_fields:
            if not field.concrete or field.is_relation:
                continue
            conflict_fields.extend(self._conflict_fields_from_field(field))
        return {df.name: df for df in conflict_fields}

    def _conflict_fields_from_field(self, field):
        def clone_field(prefix):
            field_type = type(field)
            kwargs = {"name": f"{prefix}{field.name}"}

            # copy these kwargs if they exist
            optional = ("primary_key", "target_field", "base_field")
            for kw in optional:
                if kw in field.__dict__:
                    kwargs[kw] = field.__dict__[kw]
            return field_type(**kwargs)

        return [clone_field(pre) for pre in ("our_", "their_", "base_")]
