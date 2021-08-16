from django.db import connection


def dolt_autocommit_migration(sender, **kwargs):
    msg = "created dolt commit for database migration"
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
