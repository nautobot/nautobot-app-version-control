from django.db import NotSupportedError
from django.db.models.expressions import Func, Value
from django.db.models import TextField
from django.db.models.fields.json import JSONField


class JSONObject(Func):
    function = "JSON_OBJECT"
    output_field = JSONField()

    def __init__(self, **fields):
        expressions = []
        for key, value in fields.items():
            expressions.extend((Value(key), value))
        super().__init__(*expressions)

    def as_sql(self, compiler, connection, **extra_context):
        return super().as_sql(compiler, connection, **extra_context)
