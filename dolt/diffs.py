from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q, F, Subquery, OuterRef, Value

from nautobot.dcim.tables import cables, devices, devicetypes, power, racks, sites
from nautobot.circuits import tables as circuits_tables
from nautobot.ipam import tables as ipam_tables
from nautobot.tenancy import tables as tenancy_tables
from nautobot.virtualization import tables as virtualization_tables
from nautobot.utilities.querysets import RestrictedQuerySet
from nautobot.utilities.tables import BaseTable

from dolt.dynamic.diff_factory import DiffModelFactory, DiffListViewFactory
from dolt.dynamic.model_view_map import content_type_has_diff_view_table
from dolt.models import Commit
from dolt.versioning import db_for_commit
from dolt.functions import JSONObject


def diffable_content_types():
    # todo: once available, use https://github.com/nautobot/nautobot/issues/748
    return ContentType.objects.filter(
        app_label__in=(
            "dcim",
            "circuits",
            "ipam",
            "tenancy",
            "virtualization",
        )
    )


def three_dot_diffs(from_commit=None, to_commit=None):
    if not (from_commit and to_commit):
        raise ValueError("must specify both a to_commit and from_commit")
    merge_base = Commit.merge_base(from_commit, to_commit)
    return two_dot_diffs(from_commit=merge_base, to_commit=to_commit)


def two_dot_diffs(from_commit=None, to_commit=None):
    if not (from_commit and to_commit):
        raise ValueError("must specify both a to_commit and from_commit")

    diff_results = []
    for content_type in diffable_content_types():
        if not content_type_has_diff_view_table(content_type):
            continue

        factory = DiffModelFactory(content_type)
        diffs = factory.get_model().objects.filter(
            from_commit=from_commit, to_commit=to_commit
        )
        to_queryset = (
            content_type.model_class()
            .objects.filter(pk__in=diffs.values_list("to_id", flat=True))
            .annotate(
                diff=Subquery(
                    diffs.annotate(
                        obj=JSONObject(
                            root=Value("to", output_field=models.CharField()),
                            **diff_annotation_query_fields(diffs.model),
                        )
                    )
                    .filter(to_id=OuterRef("id"))
                    .values("obj"),
                    output_field=models.JSONField(),
                ),
            )
            .using(db_for_commit(to_commit))
        )

        from_queryset = (
            content_type.model_class()
            .objects.filter(
                # we only want deleted rows in this queryset
                # modified rows come from `to_queryset`
                pk__in=diffs.filter(diff_type="removed").values_list(
                    "from_id", flat=True
                )
            )
            .annotate(
                diff=Subquery(
                    diffs.annotate(
                        obj=JSONObject(
                            root=Value("from", output_field=models.CharField()),
                            **diff_annotation_query_fields(diffs.model),
                        )
                    )
                    .filter(from_id=OuterRef("id"))
                    .values("obj"),
                    output_field=models.JSONField(),
                ),
            )
            # "time-travel" query the database at `from_commit`
            .using(db_for_commit(from_commit))
        )

        diff_rows = sorted(list(to_queryset) + list(from_queryset), key=lambda d: d.pk)
        if not len(diff_rows):
            continue

        diff_view_table = DiffListViewFactory(content_type).get_table_model()
        diff_results.append(
            {
                "name": f"{factory.source_model_verbose_name} Diffs",
                "table": diff_view_table(diff_rows),
                "added": diffs.filter(diff_type="added").count(),
                "modified": diffs.filter(diff_type="modified").count(),
                "removed": diffs.filter(diff_type="removed").count(),
            }
        )
    return diff_results


def diff_annotation_query_fields(model):
    names = [
        f.name
        for f in model._meta.get_fields()
        # field names containing "__" cannot be
        # diffed as Django interprets kwargs with
        # "__" as lookups
        if "__" not in f.name
    ]
    return {name: F(name) for name in names}

    #
    #
    # json_str = serialize("json", [obj])
    # data = json.loads(json_str)[0]["fields"]
    #
    # # Include custom_field_data as "custom_fields"
    # if hasattr(obj, "_custom_field_data"):
    #     data["custom_fields"] = data.pop("_custom_field_data")
    #
    # # Include any tags. Check for tags cached on the instance; fall back to using the manager.
    # if is_taggable(obj):
    #     tags = getattr(obj, "_tags", []) or obj.tags.all()
    #     data["tags"] = [tag.name for tag in tags]
    #
    # # Append any extra data
    # if extra is not None:
    #     data.update(extra)
    #
    # # Copy keys to list to avoid 'dictionary changed size during iteration' exception
    # for key in list(data):
    #     # Private fields shouldn't be logged in the object change
    #     if isinstance(key, str) and key.startswith("_"):
    #         data.pop(key)
    #
    #     # Explicitly excluded keys
    #     if isinstance(exclude, (list, tuple)) and key in exclude:
    #         data.pop(key)
    #
    # return data
