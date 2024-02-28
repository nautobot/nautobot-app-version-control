from django.db import connection


def auto_dolt_commit_migration(sender, **kwargs):
    msg = "Completed database migration"
    author = "system <nautobot@nautobot.invalid>"
    with connection.cursor() as cursor:
        cursor.execute("CALL dolt_add('-A');")
        cursor.execute(
            f"""
            CALL dolt_commit(
                '--all',
                '--message', '{msg}',
                '--author', '{author}');"""
        )
