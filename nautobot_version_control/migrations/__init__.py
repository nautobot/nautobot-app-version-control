from django.db import connection


def auto_dolt_commit_migration(sender, **kwargs):
    msg = "Completed database migration"
    author = "system <nautobot@nautobot.invalid>"
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
