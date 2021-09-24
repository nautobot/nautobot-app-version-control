"""
Functions.py represents custom SQL functions that do not fit the django orm
"""

from django.db.models.expressions import Func, Value
from django.db.models.fields.json import JSONField


#pylint: disable=W0223
class JSONObject(Func):
    """ JSonObject represents the json_object mysql function """

    function = "JSON_OBJECT"
    output_field = JSONField()

    def __init__(self, **fields):
        expressions = []
        for key, value in fields.items():
            expressions.extend((Value(key), value))
        super().__init__(*expressions)

    def as_sql(self, compiler, connection, function=None, template=None, **extra_context):
        """ overrides Func class as_sql """
        return super().as_sql(compiler, connection, function, template, **extra_context)
