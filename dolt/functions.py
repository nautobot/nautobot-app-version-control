"""Dunctions.py represents custom SQL functions that do not fit the django orm."""

from django.db.models.expressions import Func, Value
from django.db.models.fields.json import JSONField


# pylint: disable=W0223
class JSONObject(Func):
    """JSONObject represents the json_object mysql function."""

    function = "JSON_OBJECT"
    output_field = JSONField()

    def __init__(self, **fields):
        """Add expressions."""
        expressions = []
        for key, value in fields.items():
            expressions.extend((Value(key), value))
        super().__init__(*expressions)
