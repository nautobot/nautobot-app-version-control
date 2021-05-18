from django.db import connection

from nautobot.utilities.querysets import RestrictedQuerySet


class CommitQuerySet(RestrictedQuerySet):
    def merge_base(self, branch1, branch2):
        """
        Returns the merge base of `branch1` and `branch2`
        """
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT dolt_merge_base('{branch1}','{branch2}') FROM dual;"
            )
            return self.get(commit_hash=cursor.fetchone()[0])
