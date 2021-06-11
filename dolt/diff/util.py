from django.db import connection

from dolt.diff.factory import OldDiffModelFactory


def diffable_content_types():
    from django.contrib.contenttypes.models import ContentType

    return ContentType.objects.filter(
        app_label__in=(
            "dcim",
            # "circuits",
            # "ipam",
            # "tenancy",
            # "virtualization",
        )
    )


def create_db_diff_views(apps, schema_editor, **kwargs):

    with connection.cursor() as cursor:
        for ct in diffable_content_types():
            view_def = OldDiffModelFactory(ct).db_view_definition()
            cursor.execute(view_def)
