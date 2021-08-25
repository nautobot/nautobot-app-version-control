from django.db import connection

from dolt.constants import DOLT_DEFAULT_BRANCH


def auto_dolt_commit_migration(sender, **kwargs):
    msg = "completed database migration"
    author = "nautobot <nautobot@ntc.com>"
    with connection.cursor() as cursor:
        cursor.execute("SELECT dolt_add('-A') FROM dual;")
        cursor.execute(
            f"""
            SELECT dolt_commit(
                '--all', 
                '--allow-empty',
                '--message', '{msg}',
                '--author', '{author}')
            FROM dual;"""
        )
